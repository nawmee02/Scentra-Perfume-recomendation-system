"""
Fragrance Knowledge Compiler.

Turns a perfume row into deterministic, labeled text — never raw JSON. Two views:

  compile_embedding_doc(p)  — intrinsic, stable fields only. Drives the embedding
                              and the version hash, so adding graph relations or
                              votes does NOT churn every embedding.
  compile_context_doc(p, …) — the rich document (relations, vote consensus,
                              popularity, performance) used as LLM retrieval
                              context and the reranker document.

Determinism matters: identical input → identical output → identical hash, so
embedding versioning can regenerate only what actually changed.
"""
import re
import json
import hashlib

KNOWLEDGE_SCHEMA_VERSION = "kc-v3"  # v3: drop perfume name (scent identity only)

_CONCENTRATIONS = [
    "eau de parfum", "eau de toilette", "eau de cologne", "eau fraiche",
    "extrait", "elixir", "intense", "absolu", "cologne", "parfum",
    "edp", "edt", "edc",
]
_CONC_CANON = {"edp": "eau de parfum", "edt": "eau de toilette", "edc": "eau de cologne"}
_CONC_SORTED = sorted(_CONCENTRATIONS, key=len, reverse=True)


def detect_concentration(text: str) -> str | None:
    """Longest matching concentration phrase, canonicalized (shared with the resolver)."""
    t = (text or "").lower()
    for c in _CONC_SORTED:
        if re.search(rf"\b{re.escape(c)}\b", t):
            return _CONC_CANON.get(c, c)
    return None


def base_name(name: str) -> str:
    """The collection/line key for a perfume — its name minus concentration and
    gender suffixes. 'Sauvage Eau de Parfum' / 'Sauvage Elixir' → 'sauvage', so
    concentration siblings group together (for same_collection/parent_line)."""
    n = (name or "").lower().strip()
    for c in _CONC_SORTED:
        n = re.sub(rf"\b{re.escape(c)}\b", " ", n)
    n = re.sub(r"\bfor (women and men|women|men|unisex)\b", " ", n)
    n = re.sub(r"\s+", " ", n).strip(" -·")
    return n


def accords_list(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    try:
        parsed = json.loads(raw)
        return [str(a) for a in parsed if a] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return [str(raw)]


def _line(label: str, value) -> str | None:
    value = (value or "").strip() if isinstance(value, str) else value
    return f"{label}: {value}" if value else None


def _votes_summary(raw) -> str | None:
    """Summarize a vote distribution as 'top bucket (n), second (n)'."""
    dist = _votes_dict(raw)
    if not dist:
        return None
    ordered = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    return ", ".join(f"{bucket} ({n})" for bucket, n in ordered if n)


def _votes_dict(raw) -> dict | None:
    if not raw:
        return None
    try:
        dist = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    return dist if isinstance(dist, dict) and dist else None


def _top_bucket(raw) -> str | None:
    dist = _votes_dict(raw)
    return max(dist, key=dist.get) if dist else None


def performance_consensus(p: dict) -> str | None:
    """Human consensus from vote distributions — never invented numbers (Gap 7).
    e.g. 'long lasting longevity, strong sillage'."""
    parts = []
    lt = _top_bucket(p.get("longevity_votes"))
    st = _top_bucket(p.get("sillage_votes"))
    if lt:
        parts.append(f"{lt} longevity")
    if st:
        parts.append(f"{st} sillage")
    return ", ".join(parts) or None


# Accord → mood descriptors (stable; derived, so no embedding churn).
_MOOD = {
    "vanilla": "cozy sweet", "gourmand": "cozy indulgent", "sweet": "cozy sweet",
    "amber": "warm sensual", "woody": "sophisticated grounded", "woods": "sophisticated grounded",
    "leather": "bold rugged", "fresh": "clean energizing", "citrus": "bright uplifting",
    "aquatic": "breezy clean", "marine": "breezy clean", "floral": "romantic elegant",
    "rose": "romantic classic", "spicy": "warm bold", "powdery": "soft elegant",
    "smoky": "mysterious intense", "green": "crisp natural", "fruity": "playful fresh",
    "musky": "sensual clean", "oud": "luxurious intense", "tobacco": "warm masculine",
    "aromatic": "fresh refined",
}


def mood_descriptors(accords: list[str]) -> str:
    moods: list[str] = []
    for a in accords:
        al = a.lower()
        for key, val in _MOOD.items():
            if key in al:
                moods.extend(val.split())
    return " ".join(dict.fromkeys(moods))


# --------------------------------------------------------------------------- #
# Embedding document (intrinsic, stable)
# --------------------------------------------------------------------------- #

def compile_embedding_doc(p: dict) -> str:
    name = p.get("name", "") or ""
    accords = accords_list(p.get("accords"))
    family = accords[0] if accords else ""
    perf = " ".join(x for x in [p.get("perfumer1"), p.get("perfumer2")]
                    if x and str(x).strip().lower() != "unknown")
    # NOTE: the perfume *name* is deliberately excluded from the embedding — it
    # pollutes scent search (e.g. a query 'fresh citrus' over-matching a perfume
    # literally named 'Citrus Bigarrade'). Names are still searchable via FTS
    # (sparse) and stored in the payload for display. Embeddings = scent only.
    lines = [
        _line("Brand", p.get("brand")),
        _line("Concentration", detect_concentration(name)),
        _line("Gender", p.get("gender")),
        _line("Olfactory family", family),
        _line("Main accords", ", ".join(accords)),
        _line("Top notes", p.get("top_notes")),
        _line("Heart notes", p.get("middle_notes")),
        _line("Base notes", p.get("base_notes")),
        _line("Season", p.get("inferred_season") or p.get("season")),
        _line("Occasion", p.get("occasion")),
        _line("Mood", mood_descriptors(accords)),
        _line("Performance", performance_consensus(p)),
        _line("Perfumer", perf),
    ]
    return "\n".join(x for x in lines if x)


def content_hash(p: dict) -> str:
    body = f"{KNOWLEDGE_SCHEMA_VERSION}\n{compile_embedding_doc(p)}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Context document (rich; for LLM + reranker)
# --------------------------------------------------------------------------- #

_REL_LABELS = {
    "clone_of": "Known clones", "smells_like": "Smells like",
    "flanker_of": "Flankers", "inspired_by": "Inspired by",
    "shares_dna_with": "Shares DNA with", "layered_with": "Layered with",
    "discontinued_replacement": "Replacement for", "similar_to": "Similar to",
}


def compile_context_doc(p: dict, relations: list[dict] | None = None) -> str:
    doc = compile_embedding_doc(p)
    extra: list[str] = []

    if p.get("year"):
        extra.append(_line("Release year", str(p.get("year"))))

    consensus = performance_consensus(p)
    if consensus:
        extra.append(_line("Most users report", consensus))
    perf_bits = []
    long_sum = _votes_summary(p.get("longevity_votes")) or p.get("longevity")
    sill_sum = _votes_summary(p.get("sillage_votes")) or p.get("sillage")
    if long_sum:
        perf_bits.append(f"longevity {long_sum}")
    if sill_sum:
        perf_bits.append(f"sillage {sill_sum}")
    if perf_bits:
        extra.append(_line("Vote distribution", "; ".join(perf_bits)))

    gender_sum = _votes_summary(p.get("gender_votes"))
    if gender_sum:
        extra.append(_line("Community gender vote", gender_sum))

    if p.get("rating") is not None:
        pop = f"{p.get('rating')}/5"
        if p.get("rating_count"):
            pop += f" from {p.get('rating_count')} votes"
        extra.append(_line("Popularity", pop))

    if relations:
        grouped: dict[str, list[str]] = {}
        for r in sorted(relations, key=lambda r: r.get("confidence", 0), reverse=True):
            label = _REL_LABELS.get(r.get("rel_type", ""), r.get("rel_type", ""))
            name = r.get("dst_name") or r.get("dst_frag_id")
            if name:
                grouped.setdefault(label, []).append(str(name))
        for label, names in grouped.items():
            extra.append(_line(label, ", ".join(dict.fromkeys(names))[:300]))

    parts = [doc] + [x for x in extra if x]
    return "\n".join(parts)
