"""
Background crawl scheduler.

Three jobs, all single-instance + coalescing so runs never overlap (prevents
hammering Fragrantica and SQLite write contention):
  - discover_catalog      weekly  — find new perfume URLs across all brands
  - discover_new_releases daily   — enqueue fresh releases
  - scrape_batch          30 min  — process a bounded batch, sync to Qdrant

The NawmeEssences inventory sync is stubbed for when that API is ready.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ingestion import fragrantica_scraper
import workers

log = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()


async def _sync_nawmee_inventory():
    # PLACEHOLDER: when the NawmeEssences admin API exists, pull inventory here
    # and ingestion.manual.add_or_update(item) each product (in_inventory=1).
    pass


def start_scheduler() -> None:
    scheduler.add_job(
        fragrantica_scraper.discover_catalog,
        CronTrigger(day_of_week="sun", hour=3),
        id="discover_catalog", max_instances=1, coalesce=True, replace_existing=True,
    )
    scheduler.add_job(
        fragrantica_scraper.discover_new_releases,
        CronTrigger(hour=5),
        id="discover_new", max_instances=1, coalesce=True, replace_existing=True,
    )
    scheduler.add_job(
        fragrantica_scraper.scrape_batch,
        IntervalTrigger(minutes=30),
        id="scrape_batch", max_instances=1, coalesce=True, replace_existing=True,
    )

    # Background workers (Gap 7) — all single-instance + coalescing + resumable.
    _worker_jobs = [
        ("embedding_sync", workers.job_embedding_sync, IntervalTrigger(minutes=10)),
        ("relationship_build", workers.job_relationship_build, IntervalTrigger(minutes=20)),
        ("enrichment", workers.job_enrichment, IntervalTrigger(minutes=30)),
        ("failed_retry", workers.job_failed_retry, IntervalTrigger(hours=1)),
        ("health_monitor", workers.job_health_monitor, IntervalTrigger(minutes=5)),
        ("graph_infer", workers.job_graph_infer, IntervalTrigger(hours=6)),
        ("graph_cleanup", workers.job_graph_cleanup, CronTrigger(hour=4)),
        ("season_infer", workers.job_season_infer, IntervalTrigger(minutes=15)),
    ]
    for job_id, fn, trigger in _worker_jobs:
        scheduler.add_job(fn, trigger, id=job_id, max_instances=1,
                          coalesce=True, replace_existing=True)

    scheduler.start()
    log.info("Scheduler started: crawl jobs + workers %s",
             [j for j, _, _ in _worker_jobs])


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
