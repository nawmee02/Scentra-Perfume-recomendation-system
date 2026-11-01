"""
Relationship layer.

Explicit perfume-to-perfume relationships (similar_to, clone_of, flanker_of, …)
are looked up from the graph table, NOT computed from embeddings. find_similar
prefers crowdsourced graph edges (populated when the "reminds me of" box is
scraped) and falls back to vector similarity over the structured note/accord
embedding when the graph is thin — so it degrades gracefully instead of
returning nothing.

resolve_fragrance maps a free-text reference ("Dior Sauvage", "Sauvage Elixir")
to a specific catalog row, concentration-aware, so EDT/EDP/Elixir don't collide.
"""
import re
import asyncio
import logging

from rapidfuzz import fuzz

import db
import qdrant_store
import tools
from knowledge import detect_concentration as _detect_concentration, _CONCENTRATIONS

log = logging.getLogger("relationship")

_CONC_SET = set(_CONCENTRATIONS)
_CLONE_HOUSES = {
    "armaf", "afnan", "lattafa", "lattafa perfumes", "maison alhambra",
    "fragrance world", "montblanc", "al haramain", "al-haramain", "al haramain perfumes",
    "rasasi", "paris corner", "zimaya", "swiss arabian", "in the box", "parfums vintage"
}



def resolve_fragrance(text: str, brand: str = "") -> dict | None:
    """Fuzzy, concentration-aware resolution of a reference string to a row.

    A requested concentration (EDP/Elixir/Parfum…) strongly boosts matching
    variants and penalizes the wrong concentration, so 'Sauvage Elixir' doesn't
    collapse to base Sauvage — they smell different.
    """
    text = (text or "").strip()
    if not text:
        return None

    req_conc = _detect_concentration(text)
    tokens = [t for t in re.findall(r"[a-z0-9]+", text.lower())
              if len(t) > 2 and t not in _CONC_SET]

    seen_ids = set()
    candidates = []

    # 1. High-precision sparse FTS retrieval (indexes brand and name together)
    try:
        clean_text = " ".join(tokens) if tokens else text
        for r in db.search_fts(clean_text, 60):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
    except Exception:
        pass

    # 2. Key-token LIKE fallback (handles partial/misspelled queries)
    for tok in sorted(tokens, key=len, reverse=True)[:2]:
        for r in db.search_by_name_like(tok, 40):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)

    if not candidates:
        return None

    q_set = set(tokens)

    def score(row: dict) -> float:
        raw_name = (row.get("name") or "").lower()
        raw_brand = (row.get("brand") or "").lower()
        # Clean hyphens and punctuation so multi-token names tokenize cleanly
        name = re.sub(r"[-_]+", " ", raw_name).strip()
        row_brand = re.sub(r"[-_]+", " ", raw_brand).strip()
        full_title = f"{row_brand} {name}"
        query_clean = " ".join(tokens)

        s = max(
            float(fuzz.token_set_ratio(query_clean, name)),
            float(fuzz.token_set_ratio(query_clean, full_title))
        )

        # Overlap penalty: prevent single-token subset matches from dominating multi-token queries
        cand_tokens = set(re.findall(r"[a-z0-9]+", full_title))
        if q_set:
            overlap = len(q_set & cand_tokens) / len(q_set)
            s = s * (0.35 + 0.65 * overlap)

        if brand and brand.lower() in row_brand:
            s += 15
        elif any(tok in row_brand for tok in tokens if len(tok) >= 3):
            s += 8

        if req_conc:
            cand_conc = _detect_concentration(name)
            if cand_conc == req_conc:
                s += 40
            elif cand_conc is not None:
                s -= 25          # explicitly a different concentration
            else:
                s -= 20          # base, but a specific concentration was asked for

        rc = row.get("rating_count") or 0
        if rc > 1000:
            s += 5
        if rc > 10000:
            s += 5

        return s

    candidates.sort(key=lambda r: (score(r), r.get("rating_count") or 0), reverse=True)
    best = candidates[0]
    return best if score(best) >= 60 else None

# Evidence tiers (Gap 5). Higher base weight = stronger/more explicit evidence.
# A candidate surfacing from several tiers accumulates score and provenance.
# Priority (spec): clone > flanker > inspired > same_collection > similar > embedding.
# Crowdsourced "smells_like" (the box) is strong; structural links sit mid-tier.
_REL_WEIGHT = {
    "clone_of": 1.0, "flanker_of": 0.9, "inspired_by": 0.8,
    "smells_like": 0.85, "same_collection": 0.7, "parent_line": 0.7,
    "similar_to": 0.6, "shares_dna_with": 0.5,
}
_W_PERFUMER = 0.5
_W_ACCORD = 0.6
_W_NOTE = 0.45
_W_VECTOR = 0.45   # embedding-only is the weakest evidence

_HUMAN = {
    "clone_of": "Community clone", "smells_like": "Community 'smells like'",
    "flanker_of": "Flanker", "inspired_by": "Inspired by",
    "same_collection": "Same collection", "parent_line": "Same line",
    "shares_dna_with": "Shared DNA", "similar_to": "Community similar",
    "shared_perfumer": "Same perfumer", "shared_accord": "Shared accord profile",
    "shared_note": "Shared notes", "vector": "Vector similarity",
}


def _accord_set(row: dict) -> set[str]:
    from knowledge import accords_list
    return {a.lower().strip() for a in accords_list(row.get("accords")) if a}


def _note_set(row: dict) -> set[str]:
    notes = " , ".join(str(row.get(c) or "") for c in ("top_notes", "middle_notes", "base_notes"))
    return {n.strip().lower() for n in re.split(r"[,;/]", notes) if len(n.strip()) > 2}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _compile_scent_query(p: dict) -> str:
    import knowledge
    name = p.get("name", "") or ""
    accords = knowledge.accords_list(p.get("accords"))
    family = accords[0] if accords else ""
    lines = [
        knowledge._line("Concentration", knowledge.detect_concentration(name)),
        knowledge._line("Gender", p.get("gender")),
        knowledge._line("Olfactory family", family),
        knowledge._line("Main accords", ", ".join(accords)),
        knowledge._line("Top notes", p.get("top_notes")),
        knowledge._line("Heart notes", p.get("middle_notes")),
        knowledge._line("Base notes", p.get("base_notes")),
        knowledge._line("Season", p.get("inferred_season") or p.get("season")),
        knowledge._line("Occasion", p.get("occasion")),
        knowledge._line("Mood", knowledge.mood_descriptors(accords)),
    ]
    return "\n".join(x for x in lines if x)


async def find_similar(name: str, brand: str = "", k: int = 5,
                       budget: float | None = None, query: str = "") -> dict:
    """Cascading, provenance-carrying similarity.

    Evidence tiers (priority): explicit graph edges (clone/smells_like/…) →
    clone house olfactory matching → shared accord/note fingerprint →
    dense vector. Candidates merge across tiers; each result reports WHY it
    appeared (`similarity_reason` + structured `evidence`).
    """
    seed = await asyncio.to_thread(resolve_fragrance, name, brand)
    if not seed:
        return {"seed": None, "similar": [], "source": "none"}

    seed_id = seed["id"]
    seed_name = (seed.get("name") or "").strip().lower()
    seed_brand = (seed.get("brand") or "").strip().lower()
    fid = db.frag_id(seed.get("url"))
    seed_acc, seed_notes = _accord_set(seed), _note_set(seed)
    seed_perf = (seed.get("perfumer1") or "").strip()

    is_clone = bool(re.search(
        r"\b(clone|clones|dupe|dupes|cheap|cheaper|alternative|alternatives|substitute|substitutes|budget|affordable|inexpensive)\b",
        query, re.I))

    cand: dict[int, dict] = {}

    def is_self(record: dict) -> bool:
        pid = record.get("db_id")
        if pid is not None and pid == seed_id:
            return True
        r_fid = db.frag_id(record.get("url"))
        if fid and r_fid and fid == r_fid:
            return True
        r_name = (record.get("name") or "").strip().lower()
        r_brand = (record.get("brand") or "").strip().lower()
        if r_name == seed_name and r_brand == seed_brand:
            return True
        return False

    def add(record: dict, source: str, weight: float,
            relation: str | None = None, confidence: float | None = None):
        pid = record.get("db_id")
        if pid is None or is_self(record):
            return

        cand_brand = (record.get("brand") or "").strip().lower()
        same_house = (cand_brand == seed_brand)

        if is_clone:
            if same_house:
                weight *= 0.05
            elif any(ch in cand_brand for ch in _CLONE_HOUSES):
                weight += 0.35

        cand_price = record.get("price")
        if budget is not None and cand_price is not None:
            if cand_price > budget:
                weight *= max(0.25, budget / cand_price)
            else:
                weight += 0.25

        c = cand.setdefault(pid, {"record": record, "evidence": [], "score": 0.0,
                                  "relation": None, "vec": 0.0})
        ev = {"source": source, "weight": round(weight, 3)}
        if relation:
            ev["relation"] = relation
            c["relation"] = c["relation"] or relation
        if confidence is not None:
            ev["confidence"] = round(confidence, 2)
        c["evidence"].append(ev)
        c["score"] += weight

    def enrich(record: dict, row: dict):
        """Add shared-perfumer/accord/note evidence to a candidate."""
        ja = _jaccard(seed_acc, _accord_set(row))
        if ja >= 0.40:
            add(record, "shared_accord", _W_ACCORD * ja)
        jn = _jaccard(seed_notes, _note_set(row))
        if jn >= 0.22:
            add(record, "shared_note", _W_NOTE * jn)
        if not is_clone and seed_perf and seed_perf.lower() != "unknown" and                 (row.get("perfumer1") or "").strip() == seed_perf:
            if ja >= 0.25:
                add(record, "shared_perfumer", _W_PERFUMER * ja)

    # Tier 1/2 — explicit graph edges (incl. clone_of).
    if fid:
        for e in await asyncio.to_thread(db.get_relationships, fid, None, k * 4):
            row = db.get_by_frag_id(e["dst_frag_id"])
            if not row:
                continue
            rel = e["rel_type"]
            conf = e.get("confidence") or 0.0
            base_w = _REL_WEIGHT.get(rel, 0.8) * max(conf, 0.5)
            if rel in ("same_collection", "parent_line"):
                cand_acc = _accord_set(row)
                ja = _jaccard(seed_acc, cand_acc)
                if ja < 0.30:
                    base_w *= 0.35
            add(qdrant_store.payload(row), rel, base_w, relation=rel, confidence=conf)
            enrich(qdrant_store.payload(row), row)

    # Tier 2.5 — Clone House Olfactory Matches
    if is_clone:
        con = db.get_connection()
        cur = con.cursor()
        ch_patterns = [f"%{ch}%" for ch in _CLONE_HOUSES]
        placeholders = " OR ".join("lower(brand) LIKE ?" for _ in ch_patterns)
        rows = cur.execute(f"SELECT * FROM perfumes WHERE ({placeholders}) AND id != ? LIMIT 500", (*ch_patterns, seed_id)).fetchall()
        for raw_row in rows:
            row = dict(raw_row)
            ja = _jaccard(seed_acc, _accord_set(row))
            jn = _jaccard(seed_notes, _note_set(row))
            if ja >= 0.45 or jn >= 0.30:
                rec = qdrant_store.payload(row)
                add(rec, "clone_of", 1.0 * (ja + jn), relation="clone_of")
                enrich(rec, row)

    # Tier 2.8 — Name-echo retrieval for clones/dupes across other brands
    name_tokens = [t for t in re.findall(r"[a-z0-9]+", seed_name)
                   if len(t) > 2 and t not in _CONC_SET]
    distinctive_tokens = [t for t in name_tokens if t not in ("eau", "parfum", "toilette", "for", "men", "women")]
    for tok in distinctive_tokens[:2]:
        for row in await asyncio.to_thread(db.search_by_name_like, tok, 25):
            r_brand = (row.get("brand") or "").strip().lower()
            if r_brand != seed_brand:
                rec = qdrant_store.payload(row)
                add(rec, "clone_of" if is_clone else "similar_to", 0.85, relation="inspired_by")
                enrich(rec, row)

    # Tier 3 — shared perfumer (direct; catches non-neighbours for non-clone queries).
    if not is_clone and seed_perf:
        for row in await asyncio.to_thread(db.by_perfumer, seed_perf, seed_id, 15):
            rec = qdrant_store.payload(row)
            add(rec, "shared_perfumer", _W_PERFUMER)
            enrich(rec, row)

    # Tier 6 — dense vector neighbours (scent-focused query to capture true olfactory twins).
    scent_query_txt = _compile_scent_query(seed)
    hits = await asyncio.to_thread(qdrant_store.search, scent_query_txt, 60)
    for h in hits:
        if is_self(h):
            continue
        add(h, "vector", _W_VECTOR * float(h.get("score") or 0.0))
        if h.get("db_id") in cand:
            cand[h["db_id"]]["vec"] = float(h.get("score") or 0.0)
        row = db.get_by_id(h["db_id"])
        if row:
            enrich(h, row)

    # Rank by accumulated evidence; keep cosine for inventory promotion.
    ranked = sorted(cand.values(), key=lambda c: c["score"], reverse=True)
    results = []
    for c in ranked:
        rec = c["record"]
        rec["match_score"] = round(c["score"], 3)
        rec["final_score"] = round(c["score"], 3)     # evidence drives ranking
        rec["score"] = c["vec"]                       # cosine, for inventory promotion only
        rec["relation"] = c["relation"]
        rec["evidence"] = c["evidence"]
        rec["similarity_reason"] = list(dict.fromkeys(
            _HUMAN.get(e["source"], e["source"]) for e in c["evidence"]))
        results.append(rec)

    results = tools.inventory_presentation_sort(results)[:k]
    dominant = "graph" if any(r.get("relation") for r in results) else \
        ("vector" if results else "none")
    return {"seed": qdrant_store.payload(seed), "similar": results, "source": dominant}
def record_box_relationships(src_frag_id: str, entries: list[dict],
                             rel_type: str = "smells_like",
                             source: str = "fragrantica_box",
                             mirror: bool = True) -> int:
    """Persist scraped 'reminds me of' entries as graph edges.

    `entries` = [{frag_id, url?, name?}] in box (rank) order. Confidence scales
    with rank — the top of the box is the strongest community consensus — and is
    merged via noisy-OR, so the box reinforces (never lowers) other evidence.
    Edges are mirrored for recall, flagged so originals stay distinguishable.
    """
    n = 0
    total = max(len(entries), 1)
    for i, e in enumerate(entries):
        dst = e.get("frag_id")
        if not dst:
            continue
        # Top entry ≈0.90 → tail ≈0.60.
        confidence = round(0.60 + 0.30 * (1 - i / total), 3)
        db.add_relationship(src_frag_id, dst, rel_type, confidence=confidence,
                            source=source, weight=total - i,
                            dst_url=e.get("url"), dst_name=e.get("name"))
        if mirror:
            db.add_relationship(dst, src_frag_id, rel_type, confidence=confidence,
                                source=source, weight=total - i, mirrored=1)
        n += 1
    return n
