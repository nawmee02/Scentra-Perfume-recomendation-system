"""
Agent tools + scoring.

Recommendation philosophy: global catalog is the search space, shop inventory is
a *presentation* boost — never a hard filter. So:
  - Qdrant search is pure cosine (no price/gender filter).
  - Budget/gender are attached as soft metadata for the LLM to weigh.
  - In-stock shop items only float to the top at the final presentation pass.
"""
import re
import asyncio
import logging

import db
import qdrant_store

log = logging.getLogger("tools")

STRONG_MATCH = 0.90  # score at/above which an in-stock shop item is promoted


# --------------------------------------------------------------------------- #
# Scoring / presentation
# --------------------------------------------------------------------------- #

def apply_soft_signals(results: list[dict], budget: float | None, gender: str | None) -> list[dict]:
    """Annotate results with budget/gender fit. final_score stays pure cosine."""
    g = gender.lower() if gender else None
    for r in results:
        r["final_score"] = r.get("score", 0.0)
        if budget is not None and r.get("price") is not None:
            r["_budget_match"] = r["price"] <= budget
        if g:
            rg = (r.get("gender_lc") or "").lower()
            r["_gender_match"] = (g in rg) or (rg in ("unisex",)) or (rg == g)
    return results


def inventory_presentation_sort(results: list[dict]) -> list[dict]:
    """
    Final ordering. Strong-match in-stock shop items first (preserving their
    relative score order), then everything else by score. Stable so scent
    ranking is preserved within each group.
    """
    def is_promoted(r: dict) -> bool:
        return bool(r.get("in_inventory") and r.get("in_stock")
                    and r.get("score", 0.0) >= STRONG_MATCH)

    promoted = [r for r in results if is_promoted(r)]
    rest = [r for r in results if not is_promoted(r)]
    promoted.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    rest.sort(key=lambda r: r.get("final_score", r.get("score", 0.0)), reverse=True)
    return promoted + rest


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #

async def search_fragrances(query: str, k: int = 20, budget: float | None = None,
                            gender: str | None = None) -> list[dict]:
    results = await asyncio.to_thread(qdrant_store.search, query, k)
    return apply_soft_signals(results, budget, gender)


async def find_similar(perfume_name: str, brand: str = "", k: int = 5) -> list[dict]:
    seed = await asyncio.to_thread(qdrant_store.find_by_name, perfume_name, brand)
    if not seed or seed.get("_vector") is None:
        return []
    results = await asyncio.to_thread(
        qdrant_store.search_by_vector, seed["_vector"], k, seed.get("_id")
    )
    return inventory_presentation_sort(results)


_CURRENCY_PATTERNS = [
    (re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)"), "USD"),
    (re.compile(r"£\s?(\d[\d,]*(?:\.\d{2})?)"), "GBP"),
    (re.compile(r"€\s?(\d[\d,]*(?:\.\d{2})?)"), "EUR"),
    (re.compile(r"(?:BDT|৳)\s?(\d[\d,]*)"), "BDT"),
]


def _extract_price(text: str) -> dict | None:
    for pattern, currency in _CURRENCY_PATTERNS:
        m = pattern.search(text or "")
        if m:
            try:
                return {"price": float(m.group(1).replace(",", "")),
                        "currency": currency, "confidence": 0.7}
            except ValueError:
                continue
    return None


async def search_price(perfume_name: str, brand: str = "") -> list[dict]:
    query = f"{brand} {perfume_name} perfume buy price".strip()

    def _ddg():
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=6))

    try:
        raw = await asyncio.to_thread(_ddg)
    except Exception as e:
        log.warning("price search failed: %s", e)
        return []
    return [
        {
            "title": r.get("title"),
            "url": r.get("href"),
            "snippet": r.get("body"),
            "extracted_price": _extract_price(r.get("body", "")),
        }
        for r in raw
    ]


async def get_new_releases(limit: int = 10) -> list[dict]:
    return await asyncio.to_thread(db.get_new_releases, limit)
