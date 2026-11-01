"""
Seasonal intelligence (Gap 9).

Deterministic inference of seasonal suitability from the accord profile, modulated
by community performance (heavy long-lasting scents skew cold-weather; light/fresh
skew warm). Nothing is hardcoded per-perfume and nothing is invented — it's a
transparent rule over accords + vote consensus. The result is stored separately
(perfumes.inferred_season), never overwriting crawled data.
"""
import json

# Accord keywords that pull toward each season.
_SEASON_ACCORDS = {
    "summer": ["citrus", "aquatic", "marine", "fresh", "green", "aromatic",
               "fruity", "watery", "ozonic", "coconut"],
    "spring": ["floral", "rose", "white floral", "green", "powdery", "fresh",
               "fruity", "violet", "iris"],
    "fall":   ["woody", "woods", "spicy", "tobacco", "leather", "earthy",
               "oud", "amber", "nutty"],
    "winter": ["amber", "vanilla", "gourmand", "sweet", "oud", "leather",
               "spicy", "balsamic", "resinous", "smoky", "tobacco", "chocolate"],
}

_HEAVY = {"long lasting", "eternal", "strong", "enormous"}
_LIGHT = {"very weak", "weak", "intimate"}


def _top_bucket(raw) -> str | None:
    if not raw:
        return None
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    return max(d, key=d.get) if isinstance(d, dict) and d else None


def infer_season(accords: list[str], longevity_votes=None, sillage_votes=None) -> str:
    """Return a space-joined set of suitable seasons (e.g. 'fall winter'), or
    'all seasons' when no signal dominates."""
    accord_text = " ".join(a.lower() for a in (accords or []))
    scores = {s: 0.0 for s in _SEASON_ACCORDS}
    for season, keys in _SEASON_ACCORDS.items():
        for k in keys:
            if k in accord_text:
                scores[season] += 1

    # Performance modulation: strong/long-lasting → colder; light → warmer.
    perf = {_top_bucket(longevity_votes), _top_bucket(sillage_votes)}
    if perf & _HEAVY:
        scores["winter"] += 1.5
        scores["fall"] += 1.0
    if perf & _LIGHT:
        scores["summer"] += 1.5
        scores["spring"] += 1.0

    top = max(scores.values())
    if top == 0:
        return "all seasons"
    chosen = [s for s, v in scores.items() if v >= top - 1.0 and v > 0]
    order = ["spring", "summer", "fall", "winter"]
    return " ".join(s for s in order if s in chosen)
