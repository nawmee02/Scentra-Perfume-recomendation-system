"""
Scentra agent — routed, single-call RAG (presentation layer).

Flow per request:
  route intent + extract constraints  →  retrieve via the right path
  (hybrid search / relationship lookup / price / new-releases)  →  apply inventory
  presentation  →  ONE grounded LLM explanation.

The heavy multi-iteration tool-calling loop is intentionally not on this path —
it's gated by settings.ENABLE_AGENTIC for deployments that can spend the latency.
On CPU-bound hosts this routed path gives the right answer in one LLM call.
"""
import re
import logging

import intent
import search_service
import relationship_service
import tools
import llm_client
import explainability
from settings import settings

log = logging.getLogger("agent")

SYSTEM_PROMPT = """You are Scentra, an expert AI fragrance assistant.

Recommend perfumes ONLY from the RETRIEVED list shown to you. Rules:
1. Rank by scent match first (notes, accords, mood, season, occasion).
2. "Shop Options" means ONLY items marked [IN STOCK]. If none are in stock, say
   "None of these are in our shop right now." Never invent retailers/prices.
3. Never invent perfumes not in the retrieved list.
4. One short sentence of reasoning per pick. Be concise; talk like an enthusiast,
   not a salesman. State trade-offs or uncertainty honestly.

Structure:
### Primary Recommendation
### Shop Options
### Alternatives"""

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


def _context(recs: list[dict], seed: dict | None) -> str:
    lines = []
    if seed:
        lines.append(f"Reference perfume: {seed.get('name')} by {seed.get('brand')}\n")
    for i, r in enumerate(recs, 1):
        tag = ""
        if r.get("in_inventory") and r.get("in_stock"):
            price = f", ${r['price']}" if r.get("price") is not None else ""
            tag = f"  [IN STOCK{price}]"
        accords = ", ".join(r.get("accords", [])[:5])
        notes = " / ".join(x for x in
                           [r.get("top_notes"), r.get("middle_notes"), r.get("base_notes")] if x)
        lines.append(f"{i}. {r.get('name')} by {r.get('brand')}{tag}\n"
                     f"   accords: {accords}\n   notes: {notes}")
    return "\n".join(lines)


async def _explain(query: str, kind: str, target: str,
                   recs: list[dict], seed: dict | None) -> tuple[str | None, bool]:
    if not recs or not await llm_client.check_available():
        return None, False
    if kind == "similar" and target:
        ask = f'The user wants perfumes similar to "{target}". Explain why each retrieved pick is a good match.'
    else:
        ask = f"User request: {query}\nRecommend the best matches and explain why each fits."
    prompt = f"{ask}\n\nRetrieved perfumes:\n{_context(recs, seed)}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}]
    try:
        for _ in range(2):  # one retry if the model returns empty content
            message = await llm_client.chat(messages, timeout=settings.LLM_TIMEOUT,
                                            max_tokens=settings.LLM_MAX_TOKENS)
            reply = _strip_think(message.get("content") or "")
            if reply:
                return reply, True
        return None, False
    except Exception as e:
        log.warning("LLM explain failed (%s: %s)", type(e).__name__, e)
        return None, False


def _price_reply(target: str, prices: list[dict]) -> str:
    if not prices:
        return f"I couldn't pull live prices for {target} right now (the price source may be rate-limiting)."
    lines = [f"Current listings I found for {target}:"]
    for p in prices[:5]:
        ep = p.get("extracted_price")
        tag = f" — {ep['currency']} {ep['price']}" if ep else ""
        lines.append(f"- {p.get('title','')}{tag} ({p.get('url','')})")
    return "\n".join(lines)


def _generate_offline_reply(query: str, kind: str, target: str,
                            recs: list[dict], seed: dict | None) -> str:
    """Generate an articulate, grounded expert explanation when an external LLM is unavailable."""
    if not recs:
        return f"I couldn't find a close fragrance match for '{query}'. Try describing specific notes (e.g. vanilla, bergamot, iris) or an occasion."

    lines = []
    top = recs[0]
    top_name = top.get("name", "Unknown")
    top_brand = top.get("brand", "")
    top_accords = ", ".join(top.get("accords", [])[:3])
    top_reason = top.get("rerank_reason") or (top.get("similarity_reason") and " · ".join(top["similarity_reason"]))

    in_stock_picks = [r for r in recs if r.get("in_inventory") and r.get("in_stock")]
    other_picks = [r for r in recs if r != top and r not in in_stock_picks][:3]

    if kind == "similar" and seed:
        ref_name = seed.get("name", target)
        ref_brand = seed.get("brand", "")
        lines.append(f"Here are the closest alternatives sharing the scent DNA of **{ref_name}** by {ref_brand}:")
        lines.append(f"\n### Primary Match")
        reason_desc = f" ({top_reason})" if top_reason else f" with prominent {top_accords} notes"
        lines.append(f"- **{top_name}** by {top_brand}: Closest overall profile match{reason_desc}.")
    else:
        lines.append(f"Here are top-rated fragrance recommendations for: *\"{query}\"*")
        lines.append(f"\n### Primary Recommendation")
        reason_desc = f" — {top_reason}" if top_reason else f" — balanced {top_accords} accord profile"
        lines.append(f"- **{top_name}** by {top_brand}{reason_desc}.")

    if in_stock_picks:
        lines.append(f"\n### Shop Options (Available in Store)")
        for p in in_stock_picks[:3]:
            price_tag = f" · ${p['price']}" if p.get("price") is not None else ""
            accords = ", ".join(p.get("accords", [])[:2])
            lines.append(f"- **{p.get('name')}** by {p.get('brand')}{price_tag} ({accords})")

    if other_picks:
        lines.append(f"\n### Worth Exploring")
        for p in other_picks[:2]:
            accords = ", ".join(p.get("accords", [])[:2])
            lines.append(f"- **{p.get('name')}** by {p.get('brand')} ({accords})")

    return "\n".join(lines)


async def run(query: str, k: int | None = None, mods: dict | None = None) -> dict:
    k = k or settings.FINAL_K
    kind, target = intent.route(query)
    cons = intent.extract_constraints(query)
    meta = {"intent": kind, "constraints": cons.model_dump(exclude_none=True)}

    # --- Price: not a perfume-list intent ---
    if kind == "price":
        prices = await tools.search_price(target)
        return {"reply": _price_reply(target, prices), "recommendations": [],
                "llm_used": False, "prices": prices, **meta}

    # --- Retrieve by intent ---
    seed = None
    if kind == "similar":
        result = await relationship_service.find_similar(target, k=max(k, 8))
        recs, seed = result["similar"], result["seed"]
        meta["similar_source"] = result["source"]
        if not recs:  # resolver missed → semantic fallback on the full query
            recs = await search_service.hybrid_search(query, max(k, 12), cons.budget, cons.gender)
    elif kind == "new_releases":
        recs = await tools.get_new_releases(max(k, 10))
    else:
        recs = await search_service.hybrid_search(query, max(k, 12), cons.budget, cons.gender)

    recs = tools.inventory_presentation_sort(recs)
    if mods:
        import regional
        recs = regional.apply(recs, mods)
    recs = recs[:k]
    pipeline = explainability.SIMILAR_PIPELINE if kind == "similar" else explainability.search_pipeline()
    explainability.annotate(recs, pipeline)
    reply, used = await _explain(query, kind, target, recs, seed)
    if not reply:
        reply = _generate_offline_reply(query, kind, target, recs, seed)
    return {"reply": reply, "recommendations": recs, "llm_used": used,
            "pipeline": pipeline, **meta}
