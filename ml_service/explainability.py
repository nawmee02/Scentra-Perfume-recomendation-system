"""
Explainability (Gap 8).

Attaches a machine-readable `explain` block to every recommendation so the
frontend never has to guess why an item appeared:

  {
    "retrieval_pipeline": ["FTS5", "Qdrant", "RRF"],
    "similarity_reason": ["Community 'smells like'", "Shared accord profile"],
    "graph_relation": "smells_like",
    "inventory_reason": "Available in shop inventory"
  }

Purely additive — existing response fields are untouched.
"""
from settings import settings


def search_pipeline() -> list[str]:
    stages = ["FTS5", "Qdrant", "RRF"]
    if settings.ENABLE_CROSS_ENCODER:
        stages.append("CrossEncoder")
    return stages


SIMILAR_PIPELINE = ["RelationshipGraph", "SharedPerfumer", "AccordFingerprint",
                    "NoteFingerprint", "Qdrant"]


def annotate(results: list[dict], pipeline: list[str]) -> list[dict]:
    for r in results:
        explain: dict = {"retrieval_pipeline": pipeline}
        if r.get("similarity_reason"):
            explain["similarity_reason"] = r["similarity_reason"]
        if r.get("relation"):
            explain["graph_relation"] = r["relation"]
        if r.get("evidence"):
            explain["evidence"] = r["evidence"]
        if r.get("in_inventory") and r.get("in_stock"):
            explain["inventory_reason"] = "Available in shop inventory"
        elif r.get("in_inventory"):
            explain["inventory_reason"] = "Carried by shop (out of stock)"
        if r.get("match_score") is not None:
            explain["match_score"] = r["match_score"]
        if r.get("ranking"):  # composite reranker reason codes (why ranked here)
            explain["ranking"] = r["ranking"]
        r["explain"] = explain
    return results
