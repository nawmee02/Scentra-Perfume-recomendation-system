"""
Query understanding for ranking.

Turns a free-form query into a QueryProfile: the desired vs *excluded* scent
families, occasion, and preference modifiers, plus the budget/gender/season that
intent.py already extracts (reused as-is — this module never re-implements them).

Negation is first-class: "fresh office, not sweet, no oud" must yield
desired={fresh} and excluded={sweet, oud}. Rerankers fail on exclusions first,
so parsing them explicitly is the point.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import intent
import vocab

# Words that flip a following (or hyphen-preceding) family into an exclusion.
_NEG_CUES = {"no", "not", "without", "avoid", "avoiding", "minus", "hold",
             "less", "non", "anti", "hate", "dislike", "except"}
_TOKEN_RE = re.compile(r"[a-z][a-z\-]*")

# Occasion cues -> canonical occasion.
_OCCASION_PATTERNS = [
    ("office", r"\b(office|work|workplace|professional|business|desk|cubicle)\b"),
    ("gym", r"\b(gym|sport|workout|exercise|running|athletic)\b"),
    ("club", r"\b(club|clubbing|party|nightclub|rave|going out)\b"),
    ("date", r"\b(date|romantic|seduction|bedroom|intimate|sensual|night out|evening)\b"),
    ("formal", r"\b(formal|wedding|black tie|gala|ceremony|elegant occasion)\b"),
    ("casual", r"\b(casual|everyday|daily|day to day|errand|school)\b"),
]

_UNIQUE_RE = re.compile(r"\b(unique|niche|different|unusual|distinctive|stand ?out|"
                        r"signature|weird|artistic|avant)\b", re.I)
_POPULAR_RE = re.compile(r"\b(crowd[- ]?pleaser|crowd[- ]?pleasing|safe|popular|"
                         r"mass appeal|compliment|versatile|approachable)\b", re.I)
_CHEAP_RE = re.compile(r"\b(cheap|affordable|budget|inexpensive|value|bargain)\b", re.I)
_PERF_RE = re.compile(r"\b(long[- ]?last|long[- ]?lasting|beast ?mode|performance|"
                      r"projection|powerful|strong|potent|all day)\b", re.I)


@dataclass
class QueryProfile:
    query: str
    desired_families: set[str] = field(default_factory=set)
    excluded_families: set[str] = field(default_factory=set)
    occasion: str | None = None
    season: str | None = None
    budget: float | None = None
    gender: str | None = None
    wants_unique: bool = False
    wants_popular: bool = False
    wants_cheap: bool = False
    wants_performance: bool = False


def _parse_families(query: str) -> tuple[set[str], set[str]]:
    """Split family mentions into (desired, excluded) using nearby negation cues.

    A family term is excluded if a negation cue appears within the preceding few
    tokens, or if it's written as 'oud-free' / 'no-oud'. Otherwise it's desired.
    """
    ql = query.lower()
    tokens = _TOKEN_RE.findall(ql)
    desired: set[str] = set()
    excluded: set[str] = set()

    for i, tok in enumerate(tokens):
        # "oud-free" / "sugar-free" style: the family itself carries the negation.
        base = tok.split("-")[0]
        fam = vocab.canonical_family(base) or vocab.canonical_family(tok)
        if not fam:
            continue
        negated = tok.endswith("-free") or "free" in tok.split("-")[1:]
        if not negated:
            # look back up to 3 tokens for a negation cue
            for j in range(max(0, i - 3), i):
                if tokens[j] in _NEG_CUES:
                    negated = True
                    break
        (excluded if negated else desired).add(fam)

    # An explicit exclusion always wins over an incidental desire for the same fam.
    desired -= excluded
    return desired, excluded


def _parse_occasion(query: str) -> str | None:
    ql = query.lower()
    for name, pattern in _OCCASION_PATTERNS:
        if re.search(pattern, ql):
            return name
    return None


def build(query: str, budget: float | None = None,
          gender: str | None = None) -> QueryProfile:
    """Assemble a QueryProfile. budget/gender may be passed explicitly (from the
    request) and otherwise fall back to what intent.py extracts from the text."""
    cons = intent.extract_constraints(query)
    desired, excluded = _parse_families(query)
    return QueryProfile(
        query=query,
        desired_families=desired,
        excluded_families=excluded,
        occasion=_parse_occasion(query),
        season=cons.season,
        budget=budget if budget is not None else cons.budget,
        gender=gender if gender is not None else cons.gender,
        wants_unique=bool(_UNIQUE_RE.search(query)),
        wants_popular=bool(_POPULAR_RE.search(query)),
        wants_cheap=bool(_CHEAP_RE.search(query)),
        wants_performance=bool(_PERF_RE.search(query)),
    )
