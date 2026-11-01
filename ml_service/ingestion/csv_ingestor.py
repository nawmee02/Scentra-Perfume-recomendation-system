"""
One-time seed import of the Fragrantica CSV into the SQLite master DB.

Runs only when the perfumes table is empty. Fixes the historical data issues:
the 'Middlee' column typo (handled defensively), comma-decimal ratings, and the
'unknown' perfumer sentinel.
"""
import os
import json
import logging

import pandas as pd

import db
from ingestion.tagging import infer_season, infer_occasion

log = logging.getLogger("csv_ingestor")

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fra_cleaned.csv")


def _clean(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    return s


def _perfumer(value) -> str | None:
    s = _clean(value)
    if s is None or s.lower() == "unknown":
        return None
    return s


def ingest_csv() -> int:
    df = pd.read_csv(
        CSV_PATH, sep=";", engine="python", on_bad_lines="skip", encoding="ISO-8859-1"
    )
    # Defensive: older exports name the column 'Middlee'.
    df.rename(columns={"Middlee": "Middle"}, inplace=True)

    if "Rating Value" in df.columns:
        df["Rating Value"] = (
            df["Rating Value"].astype(str).str.replace(",", ".", regex=False)
        )
        df["Rating Value"] = pd.to_numeric(df["Rating Value"], errors="coerce")
    if "Rating Count" in df.columns:
        df["Rating Count"] = pd.to_numeric(df["Rating Count"], errors="coerce")

    count = 0
    for row in df.to_dict(orient="records"):
        name = _clean(row.get("Perfume"))
        brand = _clean(row.get("Brand"))
        if not name or not brand:
            continue

        accords = [
            a for a in (_clean(row.get(f"mainaccord{i}")) for i in range(1, 6)) if a
        ]
        rating = row.get("Rating Value")
        rating_count = row.get("Rating Count")
        year = _clean(row.get("Year"))

        record = {
            "name": name,
            "brand": brand,
            "year": int(float(year)) if year and year.replace(".", "").isdigit() else None,
            "gender": _clean(row.get("Gender")),
            "top_notes": _clean(row.get("Top")),
            "middle_notes": _clean(row.get("Middle")),
            "base_notes": _clean(row.get("Base")),
            "accords": json.dumps(accords) if accords else None,
            "season": infer_season(accords) or None,
            "occasion": infer_occasion(accords) or None,
            "rating": float(rating) if pd.notna(rating) else None,
            "rating_count": int(rating_count) if pd.notna(rating_count) else None,
            "country": _clean(row.get("Country")),
            "perfumer1": _perfumer(row.get("Perfumer1")),
            "perfumer2": _perfumer(row.get("Perfumer2")),
            "url": _clean(row.get("url")),
            "source": "csv",
        }
        db.upsert_perfume(record)
        count += 1

    log.info("Seeded %d perfumes from CSV", count)
    return count
