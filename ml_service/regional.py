"""
Regional recommendation layer (Gap 10).

Post-retrieval, deterministic reasoning: given temperature / humidity / season,
nudge rankings by accord suitability (hot & humid → boost fresh/citrus/aquatic,
penalize heavy gourmand/leather/oud; cold → the reverse). This never touches
embeddings or retrieval — it's a transparent re-rank applied after the business
layer. Weather lookup uses Open-Meteo (free, no key) and is offline-safe: with no
network (or no coordinates) the modifiers are simply not applied.
"""
import logging

import httpx

import net

log = logging.getLogger("regional")

_HOT_BOOST = {"citrus": 1.30, "aquatic": 1.30, "marine": 1.25, "aromatic": 1.20,
              "fresh": 1.25, "green": 1.20, "fruity": 1.10, "ozonic": 1.2}
_HOT_PENALTY = {"gourmand": 0.70, "vanilla": 0.75, "amber": 0.80, "sweet": 0.75,
                "leather": 0.70, "oud": 0.70, "smoky": 0.70, "tobacco": 0.75,
                "balsamic": 0.80, "chocolate": 0.7}
_COLD_BOOST = {"amber": 1.30, "vanilla": 1.25, "gourmand": 1.30, "woody": 1.20,
               "oud": 1.25, "spicy": 1.20, "leather": 1.20, "sweet": 1.20,
               "balsamic": 1.20, "tobacco": 1.2}
_COLD_PENALTY = {"aquatic": 0.80, "citrus": 0.85, "marine": 0.80, "ozonic": 0.85}


async def weather(lat: float, lon: float) -> dict | None:
    """Current temperature (°C) + relative humidity via Open-Meteo, or None."""
    if not net.is_online():
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m"})
            r.raise_for_status()
            cur = r.json().get("current", {})
        return {"temp_c": cur.get("temperature_2m"),
                "humidity": cur.get("relative_humidity_2m")}
    except Exception as e:
        log.warning("weather lookup failed: %s", e)
        return None


def modifiers(temp_c: float | None = None, humidity: float | None = None,
              season: str | None = None) -> dict:
    """Accord → multiplier map for the given conditions. Empty = no adjustment."""
    mods: dict[str, float] = {}

    def merge(table: dict):
        for k, v in table.items():
            mods[k] = mods.get(k, 1.0) * v

    hot = (temp_c is not None and temp_c >= 27) or \
          (humidity is not None and humidity >= 65) or season == "summer"
    cold = (temp_c is not None and temp_c <= 12) or season == "winter"
    if hot:
        merge(_HOT_BOOST)
        merge(_HOT_PENALTY)
    if cold:
        merge(_COLD_BOOST)
        merge(_COLD_PENALTY)
    return mods


def apply(results: list[dict], mods: dict) -> list[dict]:
    """Re-rank results by accord suitability to the weather. Returns re-sorted."""
    if not mods:
        return results
    for r in results:
        accords = [a.lower() for a in (r.get("accords") or [])]
        factors = [m for key, m in mods.items() for a in accords if key in a]
        boost = sum(factors) / len(factors) if factors else 1.0
        r["regional_boost"] = round(boost, 3)
        base = r.get("final_score") or r.get("score") or 0.0
        r["final_score"] = base * boost
    return sorted(results, key=lambda r: r.get("final_score") or 0.0, reverse=True)
