"""
Background workers (Gap 7).

Each job is small, resumable, and records metrics (job_metrics table) via the
run_job wrapper — duration, item count, status, last error. They integrate into
the existing APScheduler (see scheduler.py), they don't replace it. Network jobs
respect the offline guard; the enrichment worker is opt-in (headed browser).

  embedding_sync      — push pending rows into Qdrant + refresh FTS
  relationship_build  — advance a persistent cursor, build evidence edges
  enrichment          — Playwright-harvest box/votes for popular un-enriched perfumes
  failed_retry        — requeue failed crawl targets
  health_monitor      — snapshot catalog/index counts
"""
import time
import asyncio
import logging

import db
import net
import qdrant_store
import playwright_fetch
from settings import settings

log = logging.getLogger("workers")


async def run_job(name: str, fn) -> int:
    """Time a worker, record metrics, swallow errors (never crash the scheduler)."""
    start = time.monotonic()
    status, items, error = "ok", 0, None
    try:
        items = await fn() or 0
    except Exception as e:  # noqa: BLE001 — workers must not break the loop
        status, error = "error", str(e)[:300]
        log.warning("worker %s failed: %s", name, e)
    db.record_job(name, status, items, int((time.monotonic() - start) * 1000), error)
    return items


# --- Individual jobs (return an item count) -------------------------------- #

async def embedding_sync() -> int:
    n = await qdrant_store.sync_unsynced()
    if n:
        await asyncio.to_thread(db.rebuild_fts)
    return n


async def relationship_build() -> int:
    import relationship_builder
    page = settings.REL_BUILD_PAGE
    offset = int(db.get_state("rel_cursor", "0") or 0)
    res = await asyncio.to_thread(relationship_builder.build_page, offset, page)
    db.set_state("rel_cursor", "0" if res["done"] else str(res["next_offset"]))
    return res["edges"]


async def enrichment() -> int:
    if not settings.ENABLE_ENRICHMENT_WORKER:
        return 0
    if not (net.is_online() and playwright_fetch.available()):
        return 0
    import ingestion.fragrantica_scraper as scraper
    rows = await asyncio.to_thread(db.top_unenriched, settings.ENRICHMENT_BATCH)
    edges = 0
    for r in rows:
        res = await scraper.enrich_perfume(r["url"])
        db.mark_enriched(r["id"])
        if isinstance(res, dict):
            edges += res.get("edges", 0)
    if edges:
        await qdrant_store.sync_unsynced()
    return edges


async def failed_retry() -> int:
    return await asyncio.to_thread(db.reset_failed_targets)


async def graph_infer() -> int:
    """Structural inference (concentration siblings / collection lines) over the catalog."""
    import relationship_builder
    res = await asyncio.to_thread(relationship_builder.infer_structural_relationships)
    return res["edges"]


async def graph_cleanup() -> int:
    """Graph repair — drop self/malformed edges."""
    return await asyncio.to_thread(db.cleanup_relationships)


def _season_page() -> int:
    import knowledge
    import seasonal
    page = 300
    offset = int(db.get_state("season_cursor", "0") or 0)
    rows = db.iter_perfumes(offset, page)
    updated = 0
    for r in rows:
        accords = knowledge.accords_list(r.get("accords"))
        season = seasonal.infer_season(accords, r.get("longevity_votes"),
                                       r.get("sillage_votes"))
        if season and season != r.get("inferred_season"):
            db.set_inferred_season(r["id"], season)
            updated += 1
    db.set_state("season_cursor", "0" if len(rows) < page else str(offset + len(rows)))
    return updated


async def season_infer() -> int:
    """Fill inferred_season across the catalog, a resumable page at a time."""
    return await asyncio.to_thread(_season_page)


async def health_monitor() -> int:
    db.set_state("catalog_count", str(db.count_perfumes()))
    db.set_state("qdrant_count", str(qdrant_store.count_points()))
    db.set_state("relationship_count", str(db.count_relationships()))
    db.set_state("online", "1" if net.is_online() else "0")
    return db.count_perfumes()


# --- Scheduler entrypoints (wrapped in run_job for metrics) ----------------- #

async def job_embedding_sync():
    await run_job("embedding_sync", embedding_sync)


async def job_relationship_build():
    await run_job("relationship_build", relationship_build)


async def job_enrichment():
    await run_job("enrichment", enrichment)


async def job_failed_retry():
    await run_job("failed_retry", failed_retry)


async def job_health_monitor():
    await run_job("health_monitor", health_monitor)


async def job_graph_infer():
    await run_job("graph_infer", graph_infer)


async def job_graph_cleanup():
    await run_job("graph_cleanup", graph_cleanup)


async def job_season_infer():
    await run_job("season_infer", season_infer)
