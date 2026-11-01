"""
Intent + constraint extraction.

Cheap, zero-inference routing so the agent calls the right retrieval path:
  - "similar to / like / dupe for / clone of / reminds me of X"  → relationship lookup
  - "price / cost / how much ... of/for X"                       → live price search
  - "new releases / what's new"                                   → new-releases feed
  - everything else                                               → hybrid search

Constraints (budget, gender, season) are extracted as soft preferences for the
business/presentation layer — never as retrieval filters.
"""
import re

from schemas import Constraints

_STRIP = " ?.!\"'"

SIMILAR_RE = re.compile(
    r"\b(?:similar to|like|smells? like|dupe[s]? for|dupes? of|"
    r"alternative[s]? to|reminds? me of|something like|"
    r"clone[s]? (?:of|for)|substitute[s]? for|inspired by|"
    r"closest to|equivalent to|resembles?)\s+(.+)", re.I)

PRICE_RE = re.compile(
    r"\b(?:price|cost|how much|where to buy|buy|pricing)\b.*?\b(?:of|for)\s+(.+)", re.I)
PRICE_RE2 = re.compile(r"\b(?:price|cost|how much|pricing) (?:of |for )?(.+)", re.I)
NEW_RE = re.compile(
    r"\b(?:new releases?|latest (?:perfume|fragrance|release)s?|what'?s new|"
    r"recently released)\b", re.I)


_TARGET_TAIL = re.compile(
    r"\b(?:under|below|less than|max|budget|up\s?to|cheaper than|"
    r"for (?:men|women|him|her|me)|in (?:summer|winter|spring|autumn|fall))\b.*$"
    r"|[<$].*$", re.I)


def _clean_target(s: str) -> str:
    """Strip trailing constraint clauses ('under $100', 'for men') off a reference."""
    return _TARGET_TAIL.sub("", s).strip(_STRIP)


def route(query: str) -> tuple[str, str]:
    """Return (intent, target). target is the extracted reference for
    similar/price intents, else the original query."""
    q = (query or "").strip()
    if NEW_RE.search(q):
        return ("new_releases", "")
    if m := SIMILAR_RE.search(q):
        return ("similar", _clean_target(m.group(1)))
    if m := (PRICE_RE.search(q) or PRICE_RE2.search(q)):
        return ("price", _clean_target(m.group(1)))
    return ("search", q)


_BUDGET_RE = re.compile(
    r"(?:under|below|less than|max|budget|up\s?to|cheaper than|<)\s*\$?\s*(\d+)", re.I)
_PRICE_TAG_RE = re.compile(r"\$\s*(\d+)")
_SEASONS = ["summer", "winter", "spring", "autumn", "fall"]


def extract_constraints(query: str) -> Constraints:
    ql = (query or "").lower()

    budget = None
    if m := _BUDGET_RE.search(ql):
        budget = float(m.group(1))
    elif m := _PRICE_TAG_RE.search(ql):
        budget = float(m.group(1))

    gender = None
    if re.search(r"\b(women|woman|feminine|female|her)\b", ql):
        gender = "women"
    elif re.search(r"\b(men|man|masculine|male|him)\b", ql):
        gender = "men"
    elif "unisex" in ql:
        gender = "unisex"

    season = None
    for s in _SEASONS:
        if re.search(rf"\b{s}\b", ql):
            season = "autumn" if s == "fall" else s
            break

    return Constraints(budget=budget, gender=gender, season=season)
