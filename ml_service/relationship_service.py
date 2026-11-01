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
    token = max(tokens, key=len) if tokens else text.lower()

    seen_ids = set()
    candidates = []

    # 1. High-precision sparse FTS retrieval (indexes brand and name together)
    try:
        for r in db.search_fts(text, 60):
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

    def score(row: dict) -> float:
        name = (row.get("name") or "").lower()
        row_brand = (row.get("brand") or "").lower()
        full_title = f"{row_brand} {name}"
        query_lower = text.lower()

        s = max(
            float(fuzz.token_set_ratio(query_lower, name)),
            float(fuzz.token_set_ratio(query_lower, full_title))
        )
        if brand and brand.lower() in row_brand:
            s += 12
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
        return s

    candidates.sort(key=lambda r: (score(r), r.get("rating_count") or 0), reverse=True)
    best = candidates[0]
    return best if score(best) >= 68 else None


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


async def find_similar(name: str, brand: str = "", k: int = 5) -> dict:
    """Cascading, provenance-carrying similarity.

    Evidence tiers (priority): explicit graph edges (clone/smells_like/…) →
    shared perfumer → shared accord fingerprint → shared note fingerprint →
    dense vector. Candidates merge across tiers; each result reports WHY it
    appeared (`similarity_reason` + structured `evidence`).
    """
    seed = await asyncio.to_thread(resolve_fragrance, name, brand)
    if not seed:
        return {"seed": None, "similar": [], "source": "none"}

    seed_id = seed["id"]
    fid = db.frag_id(seed.get("url"))
    seed_acc, seed_notes = _accord_set(seed), _note_set(seed)
    seed_perf = (seed.get("perfumer1") or "").strip()

    cand: dict[int, dict] = {}

    def add(record: dict, source: str, weight: float,
            relation: str | None = None, confidence: float | None = None):
        pid = record.get("db_id")
        if pid is None or pid == seed_id:
            return
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
        if seed_perf and seed_perf.lower() != "unknown" and \
                (row.get("perfumer1") or "").strip() == seed_perf:
            add(record, "shared_perfumer", _W_PERFUMER)
        ja = _jaccard(seed_acc, _accord_set(row))
        if ja >= 0.5:
            add(record, "shared_accord", _W_ACCORD * ja)
        jn = _jaccard(seed_notes, _note_set(row))
        if jn >= 0.3:
            add(record, "shared_note", _W_NOTE * jn)

    # Tier 1/2 — explicit graph edges (incl. clone_of).
    if fid:
        for e in await asyncio.to_thread(db.get_relationships, fid, None, k * 4):
            row = db.get_by_frag_id(e["dst_frag_id"])
            if not row:
                continue
            rel = e["rel_type"]
            conf = e.get("confidence") or 0.0
            add(qdrant_store.payload(row), rel,
                _REL_WEIGHT.get(rel, 0.8) * max(conf, 0.5), relation=rel, confidence=conf)
            enrich(qdrant_store.payload(row), row)

    # Tier 3 — shared perfumer (direct; catches non-neighbours).
    if seed_perf:
        for row in await asyncio.to_thread(db.by_perfumer, seed_perf, seed_id, 15):
            rec = qdrant_store.payload(row)
            add(rec, "shared_perfumer", _W_PERFUMER)
            enrich(rec, row)

    # Tier 6 — dense vector neighbours (+ tier 4/5 enrichment of the pool).
    hits = await asyncio.to_thread(qdrant_store.search, qdrant_store.build_text(seed), 30)
    for h in hits:
        if h.get("db_id") == seed_id:
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
