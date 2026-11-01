"""
Retrieval + Fusion + Ranking layer.

hybrid_search runs dense (Qdrant) and sparse (FTS5) retrieval in parallel, fuses
them with Reciprocal Rank Fusion, optionally reranks with a cross-encoder
(off by default), and annotates soft business signals. It deliberately does NOT
apply inventory ordering — that's the business/presentation layer's job, applied
after retrieval so similarity is never influenced by what the shop carries.

RRF is used instead of mixing raw scores because dense (cosine) and sparse (bm25)
scores aren't comparable; rank position is.
"""
import asyncio
import logging

import db
import qdrant_store
import query_features
import ranking
import reranker
import tools
from settings import settings

log = logging.getLogger("search")

import time

_SEARCH_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300.0  # 5 minutes in seconds

def clear_search_cache():
    _SEARCH_CACHE.clear()



def _clone_degree(rec: dict) -> int:
    """Total graph edges for a perfume — a rough popularity/clone proxy used by the
    uniqueness feature (only consulted for 'unique' queries)."""
    fid = db.frag_id(rec.get("url"))
    if not fid:
        return 0
    try:
        return len(db.get_relationships(fid, None, 50))
    except Exception:
        return 0


def _rrf(weighted_lists: list[tuple[list[int], float]], k: int) -> dict[int, float]:
    """Weighted Reciprocal Rank Fusion over (ids, weight) lists (best-first).

    Sparse (FTS) is name/keyword-heavy, so it's weighted below dense — otherwise
    a literal name match dominates descriptive scent queries."""
    scores: dict[int, float] = {}
    for ids, weight in weighted_lists:
        for rank, pid in enumerate(ids):
            scores[pid] = scores.get(pid, 0.0) + weight / (k + rank + 1)
    return scores


async def hybrid_search(query: str, k: int | None = None,
                        budget: float | None = None,
                        gender: str | None = None,
                        rerank: bool | None = None) -> list[dict]:
    k = k or settings.FINAL_K
    cache_key = f"{(query or '').strip().lower()}:{k}:{budget}:{gender}:{rerank}"
    now = time.time()
    if cache_key in _SEARCH_CACHE:
        ts, cached = _SEARCH_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return [dict(r) for r in cached]

    dense, sparse = await asyncio.gather(
        asyncio.to_thread(qdrant_store.search, query, settings.DENSE_K),
        asyncio.to_thread(db.search_fts, query, settings.SPARSE_K),
    )

    # Unify into one record per perfume id (prefer the dense payload; fill from
    # sparse rows normalized to the same shape).
    records: dict[int, dict] = {}
    dense_ids: list[int] = []
    for r in dense:
        pid = r.get("db_id")
        if pid is None:
            continue
        records[pid] = r
        dense_ids.append(pid)

    sparse_ids: list[int] = []
    for row in sparse:
        pid = row["id"]
        sparse_ids.append(pid)
        records.setdefault(pid, qdrant_store.payload(row))

    if not records:
        return []

    # Adaptive fusion: a strong top cosine means a real scent match → dense leads
    # and sparse (name/keyword) is a supporting signal. A weak, flat dense signal
    # means the query is likely a name/keyword lookup (e.g. "aventus" embeds to
    # noise) → trust the FTS index instead. This keeps descriptive search scent-
    # driven without breaking exact-name lookups.
    dense_max = max((r.get("score") or 0.0 for r in dense), default=0.0)
    # A weak, flat top cosine means the query is a name/keyword lookup ("aventus"
    # embeds to noise) → trust FTS. This is also the EXACT-NAME LOCK signal: when
    # the name-led branch fires, the literal match already dominates, so we skip
    # the composite reranker entirely to avoid subtly regressing an identity hit.
    name_led = dense_max < settings.DENSE_STRONG
    if name_led:
        dense_w, sparse_w = 0.5, 1.5
    else:
        dense_w, sparse_w = 1.0, settings.SPARSE_WEIGHT
    fused = _rrf([(dense_ids, dense_w), (sparse_ids, sparse_w)], settings.RRF_K)
    ranked = sorted(records.values(),
                    key=lambda r: fused.get(r.get("db_id"), 0.0), reverse=True)
    for r in ranked:
        r["fused_score"] = fused.get(r.get("db_id"), 0.0)

    top = ranked[: settings.FUSED_K]
    if settings.ENABLE_CROSS_ENCODER:
        top = await reranker.cross_encode(query, top)

    tools.apply_soft_signals(top, budget, gender)
    # Default sort key is the fused (or cross-encoder) score, not raw cosine.
    for r in top:
        r["final_score"] = r.get("rerank_score", r.get("fused_score", r.get("score", 0.0)))

    rerank_on = settings.ENABLE_RERANK if rerank is None else rerank
    # Exact-name LOCK: skip the reranker ONLY for genuine identity lookups — a
    # weak/flat dense signal (name_led) AND no scent intent in the query. A
    # descriptive query can also embed weakly ("sweet vanilla for winter" ~0.48),
    # but it carries family/season/occasion terms, so it must still be reranked;
    # tying the lock to name_led alone would silently drop those from ranking.
    profile = query_features.build(query, budget, gender)
    has_scent_intent = bool(
        profile.desired_families or profile.excluded_families or profile.occasion
        or profile.season or profile.wants_unique or profile.wants_popular
        or profile.wants_performance)
    lock = name_led and not has_scent_intent
    if rerank_on and not lock:
        # Composite recommendation ranking runs off the event loop (pure CPU + at
        # most a few graph lookups for 'unique' queries).
        top = await asyncio.to_thread(
            ranking.rerank, query, top[: settings.RERANK_POOL], profile=profile,
            budget=budget, gender=gender, degree_fn=_clone_degree,
        )
    final_recs = top[:k] if k else top
    _SEARCH_CACHE[cache_key] = (now, [dict(r) for r in final_recs])
    return final_recs
