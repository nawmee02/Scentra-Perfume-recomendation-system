"""
Cross-encoder reranker (BAAI/bge-reranker-v2-m3 by default).

Gated by settings.ENABLE_CROSS_ENCODER. The model is lazy-loaded on first use,
so when the flag is off this module imports for free and never touches the heavy
weights — important on CPU-bound deployments where it would add latency.
"""
import asyncio
import logging

from settings import settings

log = logging.getLogger("reranker")

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        log.info("Loading cross-encoder %s", settings.CROSS_ENCODER_MODEL)
        _model = CrossEncoder(settings.CROSS_ENCODER_MODEL)
    return _model


def _doc(c: dict) -> str:
    accords = ", ".join(c.get("accords", [])[:6])
    notes = " / ".join(x for x in
                       [c.get("top_notes"), c.get("middle_notes"), c.get("base_notes")] if x)
    return (f"{c.get('name','')} by {c.get('brand','')}. "
            f"accords: {accords}. notes: {notes}. season: {c.get('season','')}")


async def cross_encode(query: str, candidates: list[dict],
                       top_n: int | None = None) -> list[dict]:
    """Rerank candidates by scent relevance to the query. Falls back to the
    input order if the model can't load."""
    if not candidates:
        return candidates
    try:
        model = _get_model()
        pairs = [(query, _doc(c)) for c in candidates]
        scores = await asyncio.to_thread(model.predict, pairs)
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)
        candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    except Exception as e:
        log.warning("cross-encoder rerank failed (%s); keeping fused order", e)
    return candidates[:top_n] if top_n else candidates
