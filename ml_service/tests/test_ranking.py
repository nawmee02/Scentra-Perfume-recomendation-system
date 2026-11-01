"""
Unit + regression tests for the composite reranker (Phase B) and eval metrics.

CI-safe: everything runs on synthetic candidate dicts — no DB, no Qdrant, no
model. Covers the vocabulary, query parsing (incl. negation), each feature, the
anchor property (fit beats popularity), exclusion penalties, adaptive diversity,
and the reason-code contract.

Run from ml_service/:  python -m pytest tests/ -q
"""
import pytest

import vocab
import query_features as qf
import ranking
from eval import metrics


# --------------------------------------------------------------------------- #
# Vocabulary — closed set, alias folding, soft traits
# --------------------------------------------------------------------------- #

def test_families_are_closed_set():
    fams = vocab.families_of(["citrus", "warm spicy", "oud", "totally-made-up"])
    assert fams <= set(vocab.CANONICAL_FAMILIES)
    assert "citrus" in fams and "oud" in fams
    assert "amber" in fams          # "warm spicy" folds to amber
    assert "totally-made-up" not in fams


def test_alias_prefers_longer_fragment():
    # "warm spicy" (amber) should win over "spicy"
    assert vocab.canonical_family("warm spicy") == "amber"
    assert vocab.canonical_family("spicy") == "spicy"


def test_occasion_fit_is_soft_and_directional():
    fresh_office = vocab.occasion_fit("office", {"citrus", "fresh"})
    heavy_office = vocab.occasion_fit("office", {"gourmand", "oud"})
    assert fresh_office > 0.8
    assert heavy_office < 0.2
    # No occasion → no opinion (neutral), never distorting.
    assert vocab.occasion_fit(None, {"oud"}) == 0.5


# --------------------------------------------------------------------------- #
# Query parsing — desired vs excluded, occasion, modifiers
# --------------------------------------------------------------------------- #

def test_negation_splits_desired_and_excluded():
    p = qf.build("fresh citrus office scent for summer, not sweet, no oud")
    assert "citrus" in p.desired_families and "fresh" in p.desired_families
    assert "sweet" in p.excluded_families and "oud" in p.excluded_families
    assert "sweet" not in p.desired_families
    assert p.occasion == "office"
    assert p.season == "summer"


def test_hyphen_free_negation():
    p = qf.build("woody aromatic oud-free daily scent")
    assert "oud" in p.excluded_families
    assert "woody" in p.desired_families


def test_modifier_flags():
    p = qf.build("unique niche rose, long lasting, cheap")
    assert p.wants_unique and p.wants_performance and p.wants_cheap


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #

def test_bayesian_approval_shrinks_low_vote_scores():
    high_conf = ranking._approval({"rating": 4.6, "rating_count": 12000})
    low_conf = ranking._approval({"rating": 5.0, "rating_count": 3})
    # 5.0-from-3-votes must NOT beat 4.6-from-12000 after shrinkage.
    assert high_conf > low_conf
    assert ranking._approval({"rating": None}) == 0.5


def test_price_fit_respects_budget():
    assert ranking._price_fit(100, {"price": 80}) == 1.0
    assert ranking._price_fit(100, {"price": 200}) < 0.6
    assert ranking._price_fit(None, {"price": 999}) == 1.0   # no budget → no effect


def test_accord_match_neutral_without_query_accords():
    assert ranking._accord_match(set(), {"citrus"}) == 0.5
    assert ranking._accord_match({"citrus", "fresh"}, {"citrus"}) == 0.5


# --------------------------------------------------------------------------- #
# Reranker behavior — the anchor & exclusion properties
# --------------------------------------------------------------------------- #

def _pool():
    return [
        {"db_id": 1, "name": "Bright Citrus", "brand_lc": "a",
         "accords": ["citrus", "fresh", "aromatic"], "rating": 4.1,
         "rating_count": 2000, "fused_score": 0.30, "url": ""},
        {"db_id": 2, "name": "Sugar Bomb", "brand_lc": "b",
         "accords": ["sweet", "gourmand", "vanilla"], "rating": 4.6,
         "rating_count": 12000, "fused_score": 0.34, "url": ""},
        {"db_id": 3, "name": "Oud Night", "brand_lc": "c",
         "accords": ["oud", "smoky", "leather"], "rating": 4.7,
         "rating_count": 15000, "fused_score": 0.33, "url": ""},
        {"db_id": 4, "name": "Lime Splash", "brand_lc": "a",
         "accords": ["citrus", "green"], "rating": 3.9,
         "rating_count": 500, "fused_score": 0.28, "url": ""},
    ]


def test_fit_beats_popularity():
    """A well-fitting less-famous citrus must outrank the higher-rated,
    higher-fused Sugar Bomb / Oud Night on an office-citrus query."""
    out = ranking.rerank("fresh citrus office scent for summer", _pool())
    assert out[0]["name"] == "Bright Citrus"


def test_exclusion_sinks_but_does_not_drop():
    out = ranking.rerank(
        "fresh citrus office scent, not sweet, no oud", _pool())
    names = [r["name"] for r in out]
    # excluded items are still present (not hard-dropped) but at the bottom
    assert set(names) == {"Bright Citrus", "Sugar Bomb", "Oud Night", "Lime Splash"}
    assert names.index("Sugar Bomb") >= 2
    assert names.index("Oud Night") >= 2
    penalised = {r["name"] for r in out if r["ranking"]["penalties"]}
    assert penalised == {"Sugar Bomb", "Oud Night"}


def test_final_score_is_monotonic_with_order():
    out = ranking.rerank("fresh citrus office scent", _pool())
    scores = [r["final_score"] for r in out]
    assert scores == sorted(scores, reverse=True)


def test_reason_codes_contract():
    out = ranking.rerank("fresh citrus office summer", _pool())
    rk = out[0]["ranking"]
    assert set(rk) == {"final_score", "top_factors", "penalties", "diversity_adjusted"}
    assert len(rk["top_factors"]) <= 3
    assert isinstance(rk["diversity_adjusted"], bool)


def test_diversity_off_reproduces_composite_order():
    pool_a = _pool()
    pool_b = _pool()
    diverse = ranking.rerank("fresh citrus office", pool_a, diversity=0.7)
    pure = ranking.rerank("fresh citrus office", pool_b, diversity=1.0)
    # diversity=1.0 is pure composite order; the top pick is unchanged either way
    assert diverse[0]["name"] == pure[0]["name"] == "Bright Citrus"


def test_empty_pool_is_safe():
    assert ranking.rerank("anything", []) == []


def test_anti_collapse_office_does_not_mean_citrus_only():
    """Occasion fit is a soft nudge, never a gate: for a generic 'office scent'
    query (no accord terms), an excellent-fitting mildly-sweet perfume must NOT
    rank below a mediocre fresh one just because sweetness is un-officey."""
    pool = [
        {"db_id": 1, "name": "Velvet Santal", "brand_lc": "a",
         "accords": ["woody", "vanilla"], "rating": 4.5, "rating_count": 8000,
         "fused_score": 0.52, "url": ""},                      # excellent fit, mildly sweet
        {"db_id": 2, "name": "Plain Breeze", "brand_lc": "b",
         "accords": ["fresh"], "rating": 3.4, "rating_count": 250,
         "fused_score": 0.22, "url": ""},                      # mediocre but "office-safe"
        {"db_id": 3, "name": "Casual Cedar", "brand_lc": "c",
         "accords": ["woody", "fresh"], "rating": 4.0, "rating_count": 2000,
         "fused_score": 0.40, "url": ""},
        {"db_id": 4, "name": "Zesty Basic", "brand_lc": "d",
         "accords": ["citrus"], "rating": 3.7, "rating_count": 900,
         "fused_score": 0.30, "url": ""},
    ]
    out = ranking.rerank("office scent", pool)
    names = [r["name"] for r in out]
    assert names.index("Velvet Santal") < names.index("Plain Breeze")


# --------------------------------------------------------------------------- #
# Metrics — family relevance & exclusion accounting
# --------------------------------------------------------------------------- #

def test_family_gain_zeroes_on_exclusion():
    assert metrics.family_gain({"oud"}, {"citrus"}, {"oud"}) == 0.0
    assert metrics.family_gain({"citrus"}, {"citrus", "fresh"}, set()) == 0.5


def test_exclusion_violation_rate():
    ranked = [{"sweet"}, {"citrus"}, {"oud"}]
    rate = metrics.exclusion_violation_rate(ranked, {"sweet", "oud"}, 3)
    assert rate == pytest.approx(2 / 3)


def test_ndcg_rewards_correct_order():
    good = metrics.ndcg_at_k([1.0, 0.5, 0.0], 3)
    bad = metrics.ndcg_at_k([0.0, 0.5, 1.0], 3)
    assert good > bad
    assert good == pytest.approx(1.0)


def test_mrr_and_recall():
    assert metrics.mrr(["x", "target", "y"], {"target"}) == pytest.approx(0.5)
    assert metrics.recall_at_k(["a", "b", "c"], {"a", "z"}, 3) == 0.5


def test_diversity_at_k():
    homogeneous = [{"citrus", "aquatic"}] * 5
    assert metrics.diversity_at_k(homogeneous, 5) == pytest.approx(0.0)
    disjoint = [{"citrus"}, {"woody"}, {"floral"}, {"oud"}, {"green"}]
    assert metrics.diversity_at_k(disjoint, 5) == pytest.approx(1.0)
    # mixed spread sits strictly between
    mixed = [{"citrus", "fresh"}, {"citrus", "woody"}, {"amber"}]
    assert 0.0 < metrics.diversity_at_k(mixed, 3) < 1.0
    # fewer than two results → no pairwise notion of diversity
    assert metrics.diversity_at_k([{"citrus"}], 5) == 0.0
