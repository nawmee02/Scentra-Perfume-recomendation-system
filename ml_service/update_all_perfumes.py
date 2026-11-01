"""
Catalog Updater & Fragrantica Scraper Pipeline.

Refreshes and enriches all perfumes in the catalog with the latest data
from Fragrantica:
  - Enqueues all missing/unscraped perfume URLs from perfumes table
  - Fetches latest olfactory pyramids (top, heart, base notes)
  - Fetches latest community ratings, review counts, and accord percentages
  - Extracts community 'reminds me of' relationships into the knowledge graph
  - Syncs newly updated perfume documents to Qdrant vector database
  - Rebuilds SQLite FTS5 search index
"""
import os
import sys
import json
import time
import random
import asyncio
import logging
import argparse
from bs4 import BeautifulSoup

# Ensure ml_service directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import net
import qdrant_store
import relationship_service
from settings import settings
from ingestion import fragrantica_scraper
from ingestion.fragrantica_scraper import (
    _fetch, _parse_perfume, _parse_box, _has_required
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("updater")


def ensure_all_enqueued() -> int:
    """Ensure every perfume with a Fragrantica URL in the catalog is in scrape_targets."""
    con = db.get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO scrape_targets (url, brand, status, is_new, attempts, discovered_at)
        SELECT url, brand, 'pending', COALESCE(new_release, 0), 0, CURRENT_TIMESTAMP 
        FROM perfumes
        WHERE url IS NOT NULL AND url != ''
    """)
    con.commit()
    return cur.rowcount


def get_queue_stats() -> dict:
    con = db.get_connection()
    cur = con.cursor()
    total_perfumes = cur.execute("SELECT count(*) FROM perfumes").fetchone()[0]
    synced_qdrant = cur.execute("SELECT count(*) FROM perfumes WHERE qdrant_synced = 1").fetchone()[0]
    new_releases = cur.execute("SELECT count(*) FROM perfumes WHERE new_release = 1").fetchone()[0]
    total_rels = cur.execute("SELECT count(*) FROM relationships").fetchone()[0]

    status_counts = {}
    for s, c in cur.execute("SELECT status, count(*) FROM scrape_targets GROUP BY status").fetchall():
        status_counts[s] = c

    return {
        "total_perfumes": total_perfumes,
        "synced_qdrant": synced_qdrant,
        "new_releases": new_releases,
        "total_relationships": total_rels,
        "queue": status_counts,
    }


async def scrape_and_update_target(target: dict, delay_range: tuple[float, float]) -> bool:
    url = target["url"]
    brand_hint = target.get("brand")
    is_new = bool(target.get("is_new"))
    src_fid = db.frag_id(url)

    html = await asyncio.to_thread(_fetch, url)
    if not html:
        db.mark_target_failed(url, "fetch failed")
        await asyncio.sleep(random.uniform(delay_range[0] * 2, delay_range[1] * 2))
        return False

    try:
        soup = BeautifulSoup(html, "lxml")
        rec = _parse_perfume(html, url)
        if not rec.get("brand") and brand_hint:
            rec["brand"] = brand_hint

        if not rec.get("name") or not rec.get("brand"):
            db.mark_target_failed(url, "no name/brand parsed")
            return False

        if is_new:
            rec["new_release"] = 1

        db.upsert_perfume(rec)
        db.mark_target_done(url)

        # Harvest community relationships from static HTML if present
        box = _parse_box(soup, exclude_fid=src_fid)
        if src_fid and box:
            relationship_service.record_box_relationships(
                src_fid, box, rel_type="smells_like", source="fragrantica_box"
            )

        await asyncio.sleep(random.uniform(delay_range[0], delay_range[1]))
        return True
    except Exception as e:
        db.mark_target_failed(url, str(e))
        return False


async def run_update_batch(batch_size: int = 50, delay_range: tuple[float, float] = (2.0, 3.5)) -> int:
    if not net.is_online():
        log.warning("Network is offline. Pausing updater.")
        return 0

    ensure_all_enqueued()
    targets = db.get_pending_targets(batch_size)
    if not targets:
        log.info("No pending targets found in queue.")
        return 0

    log.info("Starting update batch of %d perfumes...", len(targets))
    success = 0
    t0 = time.time()

    for i, t in enumerate(targets, 1):
        ok = await scrape_and_update_target(t, delay_range)
        if ok:
            success += 1
            log.info("[%d/%d] Updated: %s", i, len(targets), t["url"].split("/")[-1])
        else:
            log.warning("[%d/%d] Failed: %s", i, len(targets), t["url"].split("/")[-1])

    elapsed = time.time() - t0
    log.info("Batch finished: %d/%d updated in %.1fs", success, len(targets), elapsed)

    if success > 0:
        log.info("Syncing updated perfumes to Qdrant vector database...")
        synced = await qdrant_store.sync_unsynced()
        log.info("Qdrant synced %d vectors.", synced)

        log.info("Rebuilding FTS sparse keyword index...")
        await asyncio.to_thread(db.rebuild_fts)
        log.info("FTS index rebuild complete.")

    return success


async def continuous_updater(batch_size: int = 40, delay_range: tuple[float, float] = (2.0, 3.5)):
    log.info("Starting continuous catalog updater in background...")
    ensure_all_enqueued()

    idle_count = 0
    total_updated = 0

    while True:
        if not net.is_online():
            log.warning("Offline — pausing continuous updater for 60 seconds...")
            await asyncio.sleep(60)
            continue

        n = await run_update_batch(batch_size, delay_range)
        total_updated += n

        if n == 0:
            idle_count += 1
            if idle_count >= 3:
                log.info("Queue is completely drained! All catalog perfumes updated.")
                break
            await asyncio.sleep(30)
        else:
            idle_count = 0

    log.info("Continuous updater stopped. Total perfumes updated: %d", total_updated)


def main():
    parser = argparse.ArgumentParser(description="Update catalog perfumes with latest data from Fragrantica.")
    parser.add_argument("--batch", type=int, default=50, help="Number of perfumes to scrape in this batch (default: 50)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously in background until queue is empty")
    parser.add_argument("--status", action="store_true", help="Display current queue and catalog status")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum delay between requests (default: 2.0s)")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Maximum delay between requests (default: 3.5s)")

    args = parser.parse_args()

    if args.status:
        ensure_all_enqueued()
        stats = get_queue_stats()
        print("=" * 70)
        print("SCENTRA CATALOG & SCRAPER STATUS")
        print("=" * 70)
        print(f"Total perfumes in catalog:        {stats['total_perfumes']}")
        print(f"Total vectors in Qdrant:          {stats['synced_qdrant']}")
        print(f"Flagged as new releases:          {stats['new_releases']}")
        print(f"Knowledge graph relationships:    {stats['total_relationships']}")
        print("\nScrape Targets Queue:")
        for s, c in stats["queue"].items():
            print(f"  - {s:<10}: {c}")
        print("=" * 70)
        return

    delay = (args.delay_min, args.delay_max)

    if args.continuous:
        asyncio.run(continuous_updater(batch_size=args.batch, delay_range=delay))
    else:
        asyncio.run(run_update_batch(batch_size=args.batch, delay_range=delay))


if __name__ == "__main__":
    main()
