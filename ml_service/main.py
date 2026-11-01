"""
Scentra ML service — FastAPI entry point.

Startup (lifespan): init SQLite → seed from CSV if empty → sync shop inventory →
build/load Qdrant → build FTS index → probe the LLM → start the crawl scheduler.

The endpoints are thin: retrieval/fusion lives in search_service, relationships in
relationship_service, intent routing in agent. If Qdrant is deleted the service
rebuilds it from SQLite on next start (SQLite is the source of truth).
"""
import os
import json
import asyncio
import sqlite3
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

import db
import qdrant_store
import search_service
import relationship_service
import relationship_builder
import knowledge
import agent
import llm_client
import tools
import schemas
import explainability
import repositories
import regional
import net
from settings import settings
from ingestion import csv_ingestor, manual, fragrantica_scraper
from scheduler import start_scheduler, shutdown as shutdown_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("main")


def _sync_shop_inventory() -> int:
    """Mirror the Node app's shop perfumes into the master DB with in_inventory=1."""
    if not os.path.exists(settings.SHOP_DB):
        log.info("Shop DB not found at %s — skipping inventory sync", settings.SHOP_DB)
        return 0
    conn = sqlite3.connect(settings.SHOP_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM perfumes").fetchall()
    except sqlite3.Error as e:
        log.warning("Could not read shop perfumes: %s", e)
        conn.close()
        return 0
    conn.close()

    count = 0
    for r in rows:
        r = dict(r)
        try:
            notes = json.loads(r.get("notes") or "[]")
        except (json.JSONDecodeError, TypeError):
            notes = []
        try:
            sizes = json.loads(r.get("sizes") or "[]")
        except (json.JSONDecodeError, TypeError):
            sizes = []
        category = r.get("category")
        manual.add_or_update({
            "name": r.get("name"),
            "brand": r.get("brand"),
            "top_notes": ", ".join(notes) if notes else None,
            "accords": [category] if category else None,
            "description": r.get("description"),
            "price": r.get("price"),
            "original_price": r.get("original_price"),
            "sizes": sizes or None,
            "image_url": r.get("image_url"),
            "rating": r.get("rating"),
            "in_inventory": 1,
            "in_stock": 1 if r.get("in_stock", 1) else 0,
            "discount": r.get("discount") or 0,
            "source": "shop",
        })
        count += 1
    log.info("Synced %d shop inventory items", count)
    return count


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if db.count_perfumes() == 0:
        log.info("Empty catalog — seeding from CSV...")
        csv_ingestor.ingest_csv()
    _sync_shop_inventory()

    qdrant_store.get_model()          # warm the encoder
    qdrant_store.init_collection()
    synced = await qdrant_store.sync_unsynced()
    log.info("Qdrant ready (%d points; %d synced this run)",
             qdrant_store.count_points(), synced)

    fts_rows = await asyncio.to_thread(db.rebuild_fts)
    log.info("FTS index built (%d rows)", fts_rows)

    await llm_client.check_available()
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()
        import playwright_fetch
        await playwright_fetch.shutdown()


app = FastAPI(title="Scentra ML Service", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "perfumes_loaded": db.count_perfumes(),
        "qdrant_points": qdrant_store.count_points(),
        "fts_rows": db.count_fts(),
        "relationships": db.count_relationships(),
        "inventory_count": db.count_inventory(),
        "llm_available": llm_client.is_available(),
        "cross_encoder": settings.ENABLE_CROSS_ENCODER,
        "online": net.is_online(),
        "crawl_active": fragrantica_scraper.crawl_active(),
        "crawl_progress": db.count_targets_by_status(),
        "jobs": {m["job"]: m["last_status"] for m in db.get_job_metrics()},
    }


@app.get("/admin/metrics")
async def admin_metrics():
    """Background-worker metrics + resumable state."""
    return {
        "jobs": db.get_job_metrics(),
        "rel_cursor": db.get_state("rel_cursor", "0"),
        "online": net.is_online(),
    }


@app.post("/admin/run-job/{name}")
async def admin_run_job(name: str):
    """Run a background worker once, on demand (same path the scheduler uses)."""
    import workers
    fn = {
        "embedding_sync": workers.embedding_sync,
        "relationship_build": workers.relationship_build,
        "enrichment": workers.enrichment,
        "failed_retry": workers.failed_retry,
        "health_monitor": workers.health_monitor,
        "graph_infer": workers.graph_infer,
        "graph_cleanup": workers.graph_cleanup,
        "season_infer": workers.season_infer,
    }.get(name)
    if fn is None:
        raise HTTPException(404, f"unknown job '{name}'")
    items = await workers.run_job(name, fn)
    return {"job": name, "items": items,
            "metrics": next((m for m in db.get_job_metrics() if m["job"] == name), None)}


async def _regional_mods(req) -> dict | None:
    """Build accord modifiers from explicit temp/humidity, else a coords weather lookup."""
    if req.temp_c is not None or req.humidity is not None:
        return regional.modifiers(req.temp_c, req.humidity)
    if req.lat is not None and req.lon is not None:
        w = await regional.weather(req.lat, req.lon)
        if w:
            return regional.modifiers(w.get("temp_c"), w.get("humidity"))
    return None


async def _search(req: schemas.SearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "query is required")
    # over-fetch a bit so the regional re-rank has candidates to reorder
    results = await search_service.hybrid_search(
        req.query, max(req.k, 12), req.budget, req.gender, rerank=req.rerank)
    ranked = tools.inventory_presentation_sort(results)
    mods = await _regional_mods(req)
    if mods:
        ranked = regional.apply(ranked, mods)
    ranked = ranked[: req.k]
    explainability.annotate(ranked, explainability.search_pipeline())
    return {"recommendations": ranked, "pipeline": explainability.search_pipeline(),
            "regional_applied": bool(mods)}


@app.post("/recommend")
async def recommend(req: schemas.SearchRequest):
    """Hybrid (dense + sparse → RRF) search. Backward-compatible with the Node proxy."""
    return await _search(req)


@app.post("/catalog/search")
async def catalog_search(req: schemas.SearchRequest):
    return await _search(req)


@app.post("/chat")
async def chat(req: schemas.ChatRequest):
    if not req.query.strip():
        raise HTTPException(400, "query is required")
    mods = await _regional_mods(req)
    return await agent.run(req.query, req.k, mods=mods)


@app.post("/similar")
async def similar(req: schemas.SimilarRequest):
    if not req.name.strip():
        raise HTTPException(400, "name is required")
    result = await relationship_service.find_similar(req.name, req.brand, req.k)
    if result["seed"] is None:
        raise HTTPException(404, f"Perfume '{req.name}' not found")
    explainability.annotate(result["similar"], explainability.SIMILAR_PIPELINE)
    return result


@app.post("/catalog/similar")
async def catalog_similar(req: schemas.SimilarRequest):
    return await similar(req)


@app.get("/perfume/{perfume_id}")
async def get_perfume(perfume_id: int):
    # Goes through the repository layer (Gap 10) — no direct storage calls.
    perfumes = repositories.get_perfume_repo()
    relationships = repositories.get_relationship_repo()
    row = perfumes.get(perfume_id)
    if not row:
        raise HTTPException(404, "perfume not found")
    rec = qdrant_store.payload(row)
    rels = relationships.get(db.frag_id(row.get("url")) or "", limit=20)
    return {"perfume": rec, "relationships": rels}


@app.get("/new-releases")
async def new_releases(limit: int = 10):
    return {"new_releases": await tools.get_new_releases(limit)}


# --------------------------------------------------------------------------- #
# Knowledge-graph APIs (Gap 11)
# --------------------------------------------------------------------------- #

def _resolve_node(identifier: str) -> dict | None:
    """Resolve a path param (numeric id or fuzzy name) to a perfume row."""
    if identifier.isdigit():
        return db.get_by_id(int(identifier))
    return relationship_service.resolve_fragrance(identifier)


@app.get("/relationships/{perfume}")
async def get_relationships(perfume: str):
    row = _resolve_node(perfume)
    if not row:
        raise HTTPException(404, f"perfume '{perfume}' not found")
    fid = db.frag_id(row.get("url"))
    grouped: dict[str, list[dict]] = {}
    for e in (db.get_relationships(fid, None, 200) if fid else []):
        grouped.setdefault(e["rel_type"], []).append({
            "target": e.get("dst_name") or e["dst_frag_id"],
            "target_frag_id": e["dst_frag_id"],
            "confidence": round(e.get("confidence") or 0, 3),
            "sources": e.get("sources"),
        })
    return {"perfume": row.get("name"), "frag_id": fid, "relationships": grouped}


@app.get("/graph/path")
async def graph_path(from_: str = Query(alias="from"), to: str = Query(...),
                     max_depth: int = 5):
    """Shortest relationship path between two perfumes (BFS, bounded)."""
    a, b = _resolve_node(from_), _resolve_node(to)
    if not a or not b:
        raise HTTPException(404, "one or both perfumes not found")
    src, dst = db.frag_id(a.get("url")), db.frag_id(b.get("url"))
    if not src or not dst:
        raise HTTPException(400, "perfume has no graph id")

    from collections import deque
    queue, seen, visits = deque([[src]]), {src}, 0
    while queue and visits < 4000:
        path = queue.popleft()
        if len(path) > max_depth:
            continue
        for e in db.get_relationships(path[-1], None, 50):
            visits += 1
            nxt = e["dst_frag_id"]
            if nxt == dst:
                return {"path": path + [nxt], "length": len(path)}
            if nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return {"path": None, "length": None}


@app.get("/graph/{perfume}")
async def graph_node(perfume: str):
    row = _resolve_node(perfume)
    if not row:
        raise HTTPException(404, f"perfume '{perfume}' not found")
    fid = db.frag_id(row.get("url"))
    edges = [{
        "target_frag_id": e["dst_frag_id"], "target": e.get("dst_name"),
        "type": e["rel_type"], "confidence": round(e.get("confidence") or 0, 3),
    } for e in (db.get_relationships(fid, None, 100) if fid else [])]
    return {"node": {"frag_id": fid, "name": row.get("name"), "brand": row.get("brand")},
            "edges": edges}


@app.post("/graph/rebuild")
async def graph_rebuild():
    """Run structural inference over the whole catalog (background)."""
    asyncio.create_task(asyncio.to_thread(relationship_builder.infer_structural_relationships))
    return {"status": "started", "job": "infer_structural_relationships"}


@app.post("/graph/infer")
async def graph_infer(req: schemas.SimilarRequest):
    """Build evidence relationships for one perfume now (graph + structural)."""
    seed = relationship_service.resolve_fragrance(req.name, req.brand)
    if not seed:
        raise HTTPException(404, f"perfume '{req.name}' not found")
    edges = await asyncio.to_thread(relationship_builder.build_for_perfume, seed)
    return {"perfume": seed.get("name"), "evidence_edges": edges}


@app.post("/price")
async def price(req: schemas.PriceRequest):
    """Live web price search for a perfume (DuckDuckGo + currency extraction)."""
    if not req.name.strip():
        raise HTTPException(400, "name is required")
    return {"results": await tools.search_price(req.name, req.brand)}


@app.post("/admin/perfumes")
async def admin_upsert(perfume: schemas.AdminPerfume):
    record = perfume.model_dump()
    manual.add_or_update(record)
    await qdrant_store.sync_unsynced()
    return {"status": "ok", "name": record["name"], "brand": record["brand"]}


@app.post("/admin/reindex")
async def admin_reindex(stale_only: bool = False):
    """Rebuild FTS and sync pending rows into Qdrant. With stale_only=true, first
    flag rows whose embedding predates the current knowledge schema (targeted
    regeneration — never a full rebuild)."""
    marked = db.mark_stale_embeddings(knowledge.KNOWLEDGE_SCHEMA_VERSION) if stale_only else 0
    synced = await qdrant_store.sync_unsynced()
    fts_rows = await asyncio.to_thread(db.rebuild_fts)
    return {"status": "ok", "marked_stale": marked, "fts_rows": fts_rows,
            "qdrant_synced": synced, "qdrant_points": qdrant_store.count_points(),
            "embedding_schema": knowledge.KNOWLEDGE_SCHEMA_VERSION}


@app.post("/admin/build-relationships")
async def build_relationships(offset: int = 0, limit: int = 200):
    """Run the evidence-based relationship builder over a page of the catalog."""
    return await asyncio.to_thread(relationship_builder.build_page, offset, limit)


@app.post("/admin/enrich")
async def admin_enrich(req: schemas.SimilarRequest):
    """Playwright-render a perfume and harvest its 'reminds me of' box + votes
    into the graph (high-confidence community evidence). Requires Playwright."""
    seed = await asyncio.to_thread(relationship_service.resolve_fragrance, req.name, req.brand)
    if not seed or not seed.get("url"):
        raise HTTPException(404, f"Perfume '{req.name}' not found / has no URL")
    return await fragrantica_scraper.enrich_perfume(seed["url"])


# --- On-demand crawl triggers (the scheduler runs these automatically too) ---

@app.post("/admin/crawl/new-releases")
async def crawl_new_releases():
    asyncio.create_task(fragrantica_scraper.discover_new_releases())
    return {"status": "started", "job": "discover_new_releases"}


@app.post("/admin/crawl/discover")
async def crawl_discover():
    asyncio.create_task(fragrantica_scraper.discover_catalog())
    return {"status": "started", "job": "discover_catalog"}


@app.post("/admin/crawl/scrape")
async def crawl_scrape(batch_size: int = 20):
    asyncio.create_task(fragrantica_scraper.scrape_batch(batch_size))
    return {"status": "started", "job": "scrape_batch", "batch_size": batch_size}


@app.post("/admin/crawl/full")
async def crawl_full():
    """Discover the whole catalog (deduped by perfume id) and continuously scrape
    the missing perfumes until the queue drains. Background; idempotent."""
    if fragrantica_scraper.crawl_active():
        return {"status": "already_running"}
    asyncio.create_task(fragrantica_scraper.full_crawl())
    return {"status": "started", "job": "full_crawl"}


@app.post("/admin/crawl/stop")
async def crawl_stop():
    fragrantica_scraper.stop_crawl()
    return {"status": "stopping"}
