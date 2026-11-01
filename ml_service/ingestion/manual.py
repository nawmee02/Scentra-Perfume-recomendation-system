"""
Manual / admin perfume upsert — used by POST /admin/perfumes and the
NawmeEssences inventory sync. A thin COALESCE wrapper that flags inventory items.
"""
import json

import db


def add_or_update(record: dict) -> None:
    """
    Upsert a perfume, normalizing list fields to JSON. If price or in_inventory
    is supplied, the row is treated as a shop item. Existing scent data is never
    overwritten with NULL (COALESCE in db.upsert_perfume).
    """
    rec = dict(record)
    for key in ("accords", "sizes"):
        if isinstance(rec.get(key), list):
            rec[key] = json.dumps(rec[key])

    if rec.get("price") is not None or rec.get("in_inventory"):
        rec["in_inventory"] = 1
        rec.setdefault("in_stock", 1)
        rec.setdefault("source", "manual")

    db.upsert_perfume(rec)
