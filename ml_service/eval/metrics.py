"""
Ranking metrics — pure functions, no I/O, no ranking imports.

Two ground truths per query:
  - FAMILY relevance (primary): does the ranked list surface the expected scent
    families, and does it keep *excluded* families out? Robust in a 31K catalog
    where naming a single "correct" perfume is subjective.
  - NAMED relevance (secondary): for queries with a canonical answer (exact-name,
    a few descriptive), graded recall / MRR / nDCG over specific perfumes.

Relevance uses the canonical closed family set, so scores are interpretable.
"""
from __future__ import annotations

import math


# --------------------------------------------------------------------------- #
# Family-based (primary)
# --------------------------------------------------------------------------- #

def family_gain(fams: set[str], expected: set[str], excluded: set[str]) -> float:
    """Graded gain for one result: rewards overlap with expected families,
    zeroes-out anything that violates a stated exclusion."""
    if excluded and (fams & excluded):
        return 0.0
    if not expected:
        return 0.0
    return len(fams & expected) / len(expected)


def _dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(gains: list[float], k: int) -> float:
    gains = gains[:k]
    ideal = sorted(gains, reverse=True)
    idcg = _dcg(ideal)
    return _dcg(gains) / idcg if idcg > 0 else 0.0


def family_precision_at_k(ranked_families: list[set[str]], expected: set[str],
                          k: int) -> float:
    if not expected:
        return 0.0
    top = ranked_families[:k]
    if not top:
        return 0.0
    hits = sum(1 for fams in top if fams & expected)
    return hits / len(top)


def exclusion_violation_rate(ranked_families: list[set[str]], excluded: set[str],
                             k: int) -> float:
    """Fraction of the top-k that hits a stated exclusion (lower is better)."""
    if not excluded:
        return 0.0
    top = ranked_families[:k]
    if not top:
        return 0.0
    return sum(1 for fams in top if fams & excluded) / len(top)


def diversity_at_k(ranked_families: list[set[str]], k: int) -> float:
    """1 − mean pairwise family-Jaccard over the top-k.

    A *diagnostic*, never an optimization target: it detects when the top of the
    list turns homogeneous (7 citrus-aquatics → low) even while relevance stays
    high. MMR in the ranking layer remains the only diversity actuator."""
    top = [f for f in ranked_families[:k]]
    if len(top) < 2:
        return 0.0
    sims, pairs = 0.0, 0
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            a, b = top[i], top[j]
            union = a | b
            sims += (len(a & b) / len(union)) if union else 0.0
            pairs += 1
    return 1.0 - (sims / pairs)


# --------------------------------------------------------------------------- #
# Name-based (secondary; only when expected_perfumes exist)
# --------------------------------------------------------------------------- #

def recall_at_k(ranked_names: list[str], expected_names: set[str], k: int) -> float:
    if not expected_names:
        return 0.0
    top = set(ranked_names[:k])
    return len(top & expected_names) / len(expected_names)


def mrr(ranked_names: list[str], expected_names: set[str]) -> float:
    for i, n in enumerate(ranked_names):
        if n in expected_names:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_named_at_k(ranked_names: list[str], grades: dict[str, int], k: int) -> float:
    gains = [float(grades.get(n, 0)) for n in ranked_names[:k]]
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = _dcg([float(g) for g in ideal])
    return _dcg(gains) / idcg if idcg > 0 else 0.0
