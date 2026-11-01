"""
Composite reranker — turns a retrieved pool into a *ranked recommendation*.

Retrieval answers "which perfumes are relevant?"; this module answers "which
should come first?" — the way an enthusiast weighs a pick: scent fit first, then
occasion/season, then soft modifiers (community approval, performance, price),
then diversity so the top-k isn't five near-identical fragrances.

Design guarantees (from the plan):
  - Semantic + accord + occasion + season are the ANCHOR. Modifier weights
    (approval/performance/price) are capped below the backbone, so a popular but
    off-query perfume can't outrank a well-fitting less-famous one.
  - Stated exclusions ("no oud") apply a strong multiplicative penalty — the item
    sinks but isn't hard-dropped (a faint trace shouldn't nuke an otherwise perfect
    match).
  - Uniqueness is neutral by default; it only matters when the query asks for it.
  - Diversity (MMR) is adaptive and is turned OFF for exact-name lookups upstream
    (those bypass this module entirely).

Pure and dependency-light: every feature reads fields already on the record, so
the reranker is unit-testable with synthetic dicts (no DB / no Qdrant). The one
optional external signal — clone-graph degree for uniqueness — is injected as a
callable and only consulted when a "unique" query actually needs it.
"""
from __future__ import annotations

import math
from typing import Callable

import vocab
import query_features
from settings import settings

# All backbone/modifier features. availability & mass_appeal are computed as
# metadata but carry weight 0 in v1 (see settings.RANK_WEIGHTS).
_FEATURE_ORDER = ["semantic", "accord_match", "occasion_fit", "season_fit",
                  "approval", "performance", "price_fit", "uniqueness"]

# Community rating prior (Bayesian shrink): global mean and its equivalent votes.
_RATING_PRIOR_MEAN = 3.7   # ~typical Fragrantica average
_RATING_PRIOR_VOTES = 50

_LONGEVITY = {"very weak": 0.1, "weak": 0.3, "moderate": 0.5,
              "long lasting": 0.85, "eternal": 1.0}
_SILLAGE = {"intimate": 0.25, "soft": 0.35, "moderate": 0.55,
            "strong": 0.85, "enormous": 1.0}

_SEASON_ADJ = {
    "summer": {"summer": 1.0, "spring": 0.6, "autumn": 0.3, "winter": 0.15},
    "winter": {"winter": 1.0, "autumn": 0.6, "spring": 0.3, "summer": 0.15},
    "spring": {"spring": 1.0, "summer": 0.6, "autumn": 0.4, "winter": 0.25},
    "autumn": {"autumn": 1.0, "winter": 0.6, "spring": 0.4, "summer": 0.25},
}


# --------------------------------------------------------------------------- #
# Individual features (each returns [0,1])
# --------------------------------------------------------------------------- #

def _accord_match(desired: set[str], fams: set[str]) -> float:
    if not desired:
        return 0.5  # query had no accord terms → no opinion
    return len(desired & fams) / len(desired)


def _approval(rec: dict) -> float:
    r = rec.get("rating")
    if r is None:
        return 0.5
    try:
        r = float(r)
    except (TypeError, ValueError):
        return 0.5
    v = rec.get("rating_count") or 0
    m = _RATING_PRIOR_VOTES
    adjusted = (v / (v + m)) * r + (m / (v + m)) * _RATING_PRIOR_MEAN
    return max(0.0, min(1.0, adjusted / 5.0))


def _bucket_score(text: str, table: dict[str, float]) -> float | None:
    t = (text or "").lower()
    for key, val in table.items():
        if key in t:
            return val
    return None


def _performance(rec: dict) -> float:
    lo = _bucket_score(rec.get("longevity"), _LONGEVITY)
    si = _bucket_score(rec.get("sillage"), _SILLAGE)
    vals = [x for x in (lo, si) if x is not None]
    return sum(vals) / len(vals) if vals else 0.5  # unknown → neutral


def _season_fit(profile_season: str | None, rec: dict) -> float:
    if not profile_season:
        return 0.5
    rs = (rec.get("season") or "").lower().strip()
    if not rs:
        return 0.5
    table = _SEASON_ADJ.get(profile_season, {})
    best = 0.0
    for token, val in table.items():
        if token in rs:
            best = max(best, val)
    return best or 0.3


def _price_fit(budget: float | None, rec: dict) -> float:
    if budget is None:
        return 1.0  # no constraint → uniform, no effect on ordering
    price = rec.get("price")
    if price is None:
        return 0.6  # unpriced global-catalog item — can't confirm, mild neutral
    try:
        price = float(price)
    except (TypeError, ValueError):
        return 0.6
    if price <= budget:
        return 1.0
    return max(0.0, 1.0 - (price - budget) / budget)


def _uniqueness(rec: dict, degree_fn: Callable[[dict], int] | None) -> float:
    if degree_fn is None:
        return 0.5  # neutral when the graph signal isn't available/needed
    degree = degree_fn(rec)
    return 1.0 / (1.0 + max(0, degree))


# --------------------------------------------------------------------------- #
# Weights
# --------------------------------------------------------------------------- #

def weights_for(profile: query_features.QueryProfile) -> dict[str, float]:
    """Base weights + query-aware boosts. Modifier boosts never lift a modifier
    above the semantic/accord backbone — they only sharpen a relevant signal."""
    w = dict(settings.RANK_WEIGHTS)
    b = settings.RANK_BOOSTS
    if profile.occasion:
        w["occasion_fit"] += b["occasion"]
    if profile.season:
        w["season_fit"] += b["season"]
    if profile.budget is not None or profile.wants_cheap:
        w["price_fit"] += b["price"]
    if profile.wants_performance:
        w["performance"] += b["performance"]
    if profile.wants_unique:
        w["uniqueness"] += b["unique"]
    if profile.wants_popular:
        w["approval"] += b["popular"]
    return w


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def _semantic_norm(pool: list[dict]) -> dict[int, float]:
    """Min-max normalize the fused retrieval score within the pool → [0,1]."""
    raw = [(id(r), (r.get("fused_score") if r.get("fused_score") is not None
                    else r.get("score")) or 0.0) for r in pool]
    vals = [v for _, v in raw]
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 1e-12:
        return {rid: 1.0 for rid, _ in raw}
    return {rid: (v - lo) / span for rid, v in raw}


def _score_pool(profile, pool, degree_fn):
    """Attach per-feature values, composite (post-exclusion), and penalties."""
    weights = weights_for(profile)
    sem = _semantic_norm(pool)
    active = [f for f in _FEATURE_ORDER if weights.get(f, 0) > 0]
    wsum = sum(weights[f] for f in active) or 1.0
    # Only touch the clone graph when uniqueness actually has weight (rare "unique"
    # queries) — otherwise every search would fire a DB call per candidate.
    want_uniqueness = weights.get("uniqueness", 0) > 0

    for r in pool:
        fams = vocab.families_of(r.get("accords"))
        feats = {
            "semantic": sem[id(r)],
            "accord_match": _accord_match(profile.desired_families, fams),
            "occasion_fit": vocab.occasion_fit(profile.occasion, fams),
            "season_fit": _season_fit(profile.season, r),
            "approval": _approval(r),
            "performance": _performance(r),
            "price_fit": _price_fit(profile.budget, r),
            "uniqueness": _uniqueness(r, degree_fn) if want_uniqueness else 0.5,
        }
        composite = sum(weights[f] * feats[f] for f in active) / wsum

        penalties: list[str] = []
        hit = fams & profile.excluded_families
        if hit:
            composite *= settings.EXCLUDE_PENALTY
            penalties.append("excluded: " + ", ".join(sorted(hit)))

        contrib = {f: weights[f] * feats[f] for f in active}
        top = sorted(contrib, key=contrib.get, reverse=True)[:3]
        r["_features"] = feats
        r["composite_score"] = composite
        r["_top_factors"] = [(f, round(feats[f], 2)) for f in top]
        r["_penalties"] = penalties
    return pool


def _mmr_order(pool: list[dict], lam: float) -> list[dict]:
    """Greedy Maximal Marginal Relevance over composite score, penalizing family
    (and same-brand) redundancy so the top isn't five near-identical scents."""
    if lam >= 1.0 or len(pool) <= 2:
        return sorted(pool, key=lambda r: r["composite_score"], reverse=True)

    remaining = list(pool)
    fam_cache = {id(r): vocab.families_of(r.get("accords")) for r in pool}
    selected: list[dict] = []
    while remaining:
        best, best_val = None, -1e9
        for r in remaining:
            rel = r["composite_score"]
            if selected:
                sims = []
                for s in selected:
                    sim = vocab.family_jaccard(fam_cache[id(r)], fam_cache[id(s)])
                    if r.get("brand_lc") and r.get("brand_lc") == s.get("brand_lc"):
                        sim += settings.MMR_BRAND_SIM
                    sims.append(min(1.0, sim))
                redundancy = max(sims)
            else:
                redundancy = 0.0
            val = lam * rel - (1.0 - lam) * redundancy
            if val > best_val:
                best, best_val = r, val
        selected.append(best)
        remaining.remove(best)
    return selected


def rerank(query: str, pool: list[dict], *,
           profile: query_features.QueryProfile | None = None,
           budget: float | None = None, gender: str | None = None,
           diversity: float | None = None,
           degree_fn: Callable[[dict], int] | None = None) -> list[dict]:
    """Reorder a retrieved pool by the composite recommendation score.

    Sets `final_score` so downstream stages (inventory float, regional re-rank)
    preserve this order, attaches a debuggable `ranking` reason-code block, and
    returns the pool in final order. Pure apart from the optional `degree_fn`.
    `profile` may be supplied by the caller to avoid re-parsing the query."""
    if not pool:
        return pool
    if profile is None:
        profile = query_features.build(query, budget, gender)
    _score_pool(profile, pool, degree_fn)

    by_composite = sorted(pool, key=lambda r: r["composite_score"], reverse=True)
    composite_rank = {id(r): i for i, r in enumerate(by_composite)}

    lam = settings.MMR_LAMBDA if diversity is None else diversity
    ordered = _mmr_order(pool, lam)

    # Encode the final order into final_score with a monotone min-cascade: values
    # stay close to the composite magnitude (so the regional multiplier still means
    # something) but are strictly decreasing, so any later sort-by-final_score
    # reproduces this exact MMR order instead of collapsing back to raw score.
    prev = float("inf")
    for i, r in enumerate(ordered):
        fs = min(r["composite_score"], prev - 1e-9)
        r["final_score"] = fs
        prev = fs
        r["ranking"] = {
            "final_score": round(r["composite_score"], 4),
            "top_factors": r.pop("_top_factors"),
            "penalties": r.pop("_penalties"),
            "diversity_adjusted": composite_rank[id(r)] != i,
        }
        r.pop("_features", None)
    return ordered
