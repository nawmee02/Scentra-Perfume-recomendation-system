"""
Shared fragrance vocabulary — the single source of truth for scent families and
the soft "trait" scores used by ranking, query parsing, and the eval harness.

Why this module exists: "office-safe", "fresh", "sweet" must mean exactly ONE
thing across intent parsing, the reranker, and the benchmark. Defining them here
(and nowhere else) keeps family_precision / exclusion_violation_rate trustworthy
and prevents three slightly-different copies of the same heuristic.

Design rules:
  - CANONICAL_FAMILIES is a small, FIXED, closed set. Nothing outside it is ever
    a "family". Fragrantica accords are noisy and open-ended, so an alias map
    folds them into this closed set; anything unmapped is dropped, not invented.
  - Trait scores (freshness, loud_sweetness, heavy_smoke, ...) are SOFT and
    graded in [0,1]. There are no hard allow/deny lists — an accord "hurts" or
    "helps" a fit, it never disqualifies.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# Canonical families (closed set — 18)
# --------------------------------------------------------------------------- #
CANONICAL_FAMILIES: tuple[str, ...] = (
    "citrus", "aromatic", "fresh", "aquatic", "green", "fruity", "floral",
    "sweet", "gourmand", "vanilla", "spicy", "woody", "amber", "oud",
    "leather", "smoky", "powdery", "musky",
)
_FAMILY_SET = set(CANONICAL_FAMILIES)

# Accord/keyword fragment -> canonical family. Substring match (longest first),
# so "white floral" and "warm spicy" resolve correctly. Anything not covered
# here is intentionally ignored (kept out of the closed set).
_ALIAS: dict[str, str] = {
    # citrus
    "citrus": "citrus", "lemon": "citrus", "bergamot": "citrus",
    "orange": "citrus", "grapefruit": "citrus", "lime": "citrus",
    # aromatic / herbal
    "aromatic": "aromatic", "herbal": "aromatic", "lavender": "aromatic",
    "sage": "aromatic", "mint": "aromatic", "fougere": "aromatic",
    # fresh / ozonic
    "fresh": "fresh", "ozonic": "fresh", "clean": "fresh", "soapy": "fresh",
    "cold": "fresh",
    # aquatic / marine
    "aquatic": "aquatic", "marine": "aquatic", "water": "aquatic", "sea": "aquatic",
    # green / earthy
    "green": "green", "earthy": "green", "grass": "green", "herbaceous": "green",
    # fruity
    "fruity": "fruity", "fruit": "fruity", "apple": "fruity", "berry": "fruity",
    "peach": "fruity", "tropical": "fruity", "coconut": "fruity",
    # floral
    "floral": "floral", "flower": "floral", "rose": "floral", "jasmin": "floral",
    "iris": "floral", "violet": "floral", "tuberose": "floral", "ylang": "floral",
    "lily": "floral", "muguet": "floral",
    # sweet
    "sweet": "sweet",
    # gourmand
    "gourmand": "gourmand", "chocolate": "gourmand", "cacao": "gourmand",
    "caramel": "gourmand", "honey": "gourmand", "coffee": "gourmand",
    "almond": "gourmand", "cinnamon sugar": "gourmand",
    # vanilla
    "vanilla": "vanilla",
    # spicy
    "spicy": "spicy", "spice": "spicy", "pepper": "spicy", "cinnamon": "spicy",
    "cardamom": "spicy", "clove": "spicy", "ginger": "spicy", "saffron": "spicy",
    # woody
    "woody": "woody", "wood": "woody", "sandalwood": "woody", "cedar": "woody",
    "vetiver": "woody", "patchouli": "woody",
    # amber
    "amber": "amber", "ambery": "amber", "balsamic": "amber", "resin": "amber",
    "warm spicy": "amber",
    # oud
    "oud": "oud", "agarwood": "oud",
    # leather
    "leather": "leather", "leathery": "leather", "suede": "leather",
    # smoky
    "smoky": "smoky", "smoke": "smoky", "tobacco": "smoky", "incense": "smoky",
    "tar": "smoky",
    # powdery
    "powdery": "powdery", "powder": "powdery",
    # musky / animalic
    "musky": "musky", "musk": "musky", "animalic": "musky", "skin": "musky",
}
# Match longer fragments before shorter ones ("warm spicy" before "spicy").
_ALIAS_SORTED = sorted(_ALIAS.items(), key=lambda kv: len(kv[0]), reverse=True)


def canonical_family(term: str) -> str | None:
    """Map one accord/keyword to a canonical family, or None if unrecognized."""
    t = (term or "").lower().strip()
    if t in _FAMILY_SET:
        return t
    for frag, fam in _ALIAS_SORTED:
        if frag in t:
            return fam
    return None


def families_of(accords) -> set[str]:
    """Canonical families present in a perfume's accord list (closed set only)."""
    out: set[str] = set()
    for a in accords or []:
        fam = canonical_family(str(a))
        if fam:
            out.add(fam)
    return out


def families_from_text(text: str) -> set[str]:
    """Canonical families mentioned anywhere in free text (word-ish scan)."""
    t = (text or "").lower()
    out: set[str] = set()
    for frag, fam in _ALIAS_SORTED:
        if frag in t:
            out.add(fam)
    return out


# --------------------------------------------------------------------------- #
# Soft trait scores (graded [0,1]; no hard rules)
# --------------------------------------------------------------------------- #
_FRESH_FAMILIES = {"fresh", "citrus", "aromatic", "aquatic", "green"}
_LOUD_SWEET_FAMILIES = {"sweet", "gourmand", "vanilla"}
_HEAVY_FAMILIES = {"smoky", "oud", "leather", "amber"}


def _presence(fams: set[str], group: set[str]) -> float:
    """How strongly a family group is present (0, 0.6 for one, 1.0 for two+)."""
    n = len(fams & group)
    if n == 0:
        return 0.0
    return 0.6 if n == 1 else 1.0


def freshness(fams: set[str]) -> float:
    return _presence(fams, _FRESH_FAMILIES)


def loud_sweetness(fams: set[str]) -> float:
    return _presence(fams, _LOUD_SWEET_FAMILIES)


def heavy_smoke(fams: set[str]) -> float:
    return _presence(fams, _HEAVY_FAMILIES)


def occasion_fit(occasion: str | None, fams: set[str]) -> float:
    """Soft, graded fit of a scent profile to an occasion. Neutral (0.5) when no
    occasion is stated — the feature then has no opinion and shouldn't distort.

    Nothing is absolute: freshness helps an office scent and loud sweetness /
    heavy smoke hurt it, but a woody or faintly smoky fragrance is only nudged
    down, never excluded. Explicit exclusions are handled elsewhere."""
    if not occasion:
        return 0.5
    fresh = freshness(fams)
    loud = loud_sweetness(fams)
    heavy = heavy_smoke(fams)

    if occasion in ("office", "casual", "gym"):
        # Approachable, non-intrusive: fresh helps, loud/heavy hurt.
        score = 0.5 + 0.45 * fresh - 0.35 * loud - 0.45 * heavy
    elif occasion in ("club", "date"):
        # Projection & warmth wanted: sweet/heavy help, sheer freshness less so.
        score = 0.5 + 0.35 * loud + 0.35 * heavy - 0.20 * fresh
    elif occasion == "formal":
        # Sophisticated: woody/amber/leather help, sugary-loud reads casual.
        sophisticated = _presence(fams, {"woody", "amber", "leather", "oud", "powdery"})
        score = 0.5 + 0.4 * sophisticated - 0.25 * loud
    else:
        score = 0.5
    return max(0.0, min(1.0, score))


def family_jaccard(a: set[str], b: set[str]) -> float:
    """Similarity of two family sets (for MMR diversity)."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
