# Scentra ML Service

AI fragrance assistant: **hybrid retrieval** (dense + sparse) over a global perfume
catalog, a relationship graph for "smells like" lookups, intent-routed conversational
recommendations grounded in retrieved metadata, live price search, and a background
Fragrantica crawler that expands the catalog.

## Architecture (layered, single-responsibility)

```
                         SQLite  ── source of truth ──┐
        (catalog · inventory · crawl queue · FTS5 · relationship graph)
                                                       │
   Fragrantica ─curl_cffi→ ingestion ─────────────────┤
                                                       ▼
   ┌─────────────────── Retrieval ───────────────────────┐
   │  dense (Qdrant)        sparse (FTS5 bm25)            │
   └───────────┬───────────────────────┬─────────────────┘
               └──── RRF fusion ────────┘
                          │
              cross-encoder rerank (optional, settings flag)
                          │
              relationship expansion (graph)
                          │
              business rules (inventory presentation, budget/gender soft)
                          │
              LLM explanation (LM Studio / OpenAI-compatible)
```

Layers map to modules: `db.py` (data) · `qdrant_store.py` + `search_service.py`
(retrieval/fusion) · `reranker.py` (ranking) · `relationship_service.py` (graph) ·
`intent.py` (routing) · `agent.py` (presentation) · `settings.py` (config).

- **SQLite** (`data/perfumes.db`) — catalog + inventory flags + crawl queue + FTS5
  index + relationship graph. **The only source of truth**: delete Qdrant and the
  service rebuilds it on next start.
- **Dense** — `all-MiniLM-L6-v2` embeddings of *compiled structured docs* (name,
  brand, gender, notes, accords, season, occasion, perfumers) — never raw JSON.
- **Sparse** — SQLite FTS5 (bm25) for exact names, brands, notes, perfumers.
- **Fusion** — Reciprocal Rank Fusion (rank-based; dense cosine and sparse bm25
  aren't directly comparable).
- **Relationships** — explicit graph edges (`similar_to`, `clone_of`, `flanker_of`,
  …), queried directly, not embedded. `find_similar` is graph-first with a vector
  fallback.
- **LLM** — any OpenAI-compatible server (LM Studio default; Ollama `/v1` works).
  Graceful fallback to pure retrieval when no chat model is loaded.

## Request pipeline (`/chat`)

`route intent + extract constraints` → retrieve via the matched path (hybrid
search / relationship lookup / price / new-releases) → inventory presentation →
**one** grounded LLM explanation. Intent routing is regex (zero inference):
"similar to X" / "dupe for X" → graph lookup; "price of X" → price search;
"new releases" → feed; else hybrid search. Constraints (budget/gender/season) are
soft preferences, never retrieval filters.

## Feature flags (`settings.py`, all env-overridable)

| Flag | Default | Effect |
|------|---------|--------|
| `ENABLE_CROSS_ENCODER` | `false` | bge-reranker-v2-m3 rerank after RRF (quality↑, latency↑) |
| `ENABLE_AGENTIC` | `false` | reserved for the heavy multi-tool agent loop |

Heavy stages are **off by default** — the routed single-call path answers in one
LLM call, which matters on CPU-bound hosts.

## Setup

```bash
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001
```

First start seeds the catalog from `data/fra_cleaned.csv` (~24k perfumes), mirrors
the Node shop DB (`../server/database/perfume_finder.db`) as inventory, and encodes
everything into Qdrant (~3-5 min). Subsequent starts are fast (nothing to re-encode).

### LLM (LM Studio)

1. Start LM Studio's local server (default `http://localhost:1234`).
2. Load a **chat** model with tool support, e.g. `Qwen2.5-7B-Instruct`
   (an embedding-only model is detected and skipped — chat falls back to vector search).

The loaded chat model is auto-detected; no model id needs to be configured.

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `LLM_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | auto-detected | Override the chat model id |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | catalog/qdrant/fts/relationship counts, llm + cross-encoder status, crawl progress |
| POST | `/recommend`, `/catalog/search` | `{query, k, budget?, gender?}` → hybrid (dense+sparse→RRF) search |
| POST | `/chat` | `{query, k}` → `{reply, recommendations, intent, constraints, llm_used}` |
| POST | `/similar`, `/catalog/similar` | `{name, brand?, k}` → `{seed, similar, source}` (graph→vector, concentration-aware) |
| GET | `/perfume/{id}` | one perfume + its graph relationships |
| GET | `/new-releases` | recently crawled releases |
| GET | `/relationships/{perfume}` | graph edges for a perfume, grouped by type |
| GET | `/graph/{perfume}` | node + 1-hop edges (for visualization) |
| GET | `/graph/path?from=&to=` | shortest relationship path between two perfumes (BFS) |
| POST | `/graph/rebuild` | structural inference over the catalog (concentration siblings / lines) |
| POST | `/graph/infer` | `{name}` → build evidence edges for one perfume |
| POST | `/price` | `{name, brand?}` → live web price search |
| POST | `/admin/perfumes` | manual / inventory upsert (COALESCE — never wipes scent data) |
| POST | `/admin/reindex` | rebuild FTS index + sync pending rows into Qdrant |
| POST | `/admin/crawl/new-releases` | enqueue Fragrantica new releases now (background) |
| POST | `/admin/crawl/discover` | one-shot catalog discovery (background) |
| POST | `/admin/crawl/scrape?batch_size=N` | scrape one bounded batch of pending URLs now |
| POST | `/admin/crawl/full` | **discover the whole catalog + continuously scrape it** (concurrent, background) |
| POST | `/admin/crawl/stop` | stop the continuous scraper |
| POST | `/admin/enrich` | `{name, brand?}` → Playwright-harvest the "reminds me of" box + votes into the graph |
| POST | `/admin/build-relationships?offset&limit` | evidence-based relationship builder over a catalog page |
| POST | `/admin/reindex?stale_only=true` | rebuild FTS + re-embed only rows behind the current knowledge schema |
| GET | `/admin/metrics` | background-worker metrics + resumable cursors |
| POST | `/admin/run-job/{name}` | run a worker once on demand (embedding_sync, relationship_build, enrichment, failed_retry, health_monitor) |

### Layered retrieval, relationships & explainability

- **Knowledge compiler** (`knowledge.py`) builds the deterministic embedding doc
  (intrinsic, stable, version-hashed) and a richer context doc (relations + vote
  consensus) for the LLM/reranker. Embeddings are **versioned** — `/admin/reindex?stale_only=true`
  regenerates only rows behind the current schema, never the whole catalog.
- **Relationship graph** (`relationships`) with confidence-merged evidence
  (noisy-OR; stronger evidence never lowered). Sources: Fragrantica "reminds me
  of" box (Playwright), shared perfumer, accord/note fingerprints, manual.
- **`/similar` is a cascade** — graph → shared perfumer → accord fp → note fp →
  vector — and every result reports its `evidence` / `similarity_reason`.
- **Explainability**: `/recommend`, `/similar`, `/chat` attach an `explain` block
  (`retrieval_pipeline`, `similarity_reason`, `graph_relation`, `inventory_reason`).
- **Richer embeddings** (`kc-v2`): the doc adds mood descriptors + performance
  consensus + inferred season. Bumping `KNOWLEDGE_SCHEMA_VERSION` + `/admin/reindex?stale_only=true`
  regenerates only outdated rows.
- **Seasonal** (`seasonal.py`): accord + performance rules → `inferred_season`,
  stored separately from any crawled value (`season_infer` worker).
- **Regional** (`regional.py`): pass `lat`/`lon` (Open-Meteo lookup) or `temp_c`/`humidity`
  to `/recommend` or `/chat` → deterministic accord re-rank (hot/humid boosts fresh,
  penalizes heavy gourmand/oud). Post-retrieval only; offline-safe (no params/network = no-op).

### Two-stage crawler + offline-first

- **Stage 1** curl_cffi; **Stage 2** Playwright only when required fields are
  missing or to harvest the JS box/votes. Playwright is optional (lazy) and
  **runs headed** — Cloudflare blocks headless. Set `PLAYWRIGHT_HEADLESS=true`
  only on a host with headless-evasion.
- **Offline-first** (`net.py`): crawler/enrichment pause when offline; SQLite,
  FTS5, Qdrant, embeddings, and the LLM keep serving.

### Background workers (`workers.py`, in the scheduler)

`embedding_sync` (10m) · `relationship_build` (20m, resumable cursor) ·
`enrichment` (30m, opt-in via `ENABLE_ENRICHMENT_WORKER`) · `failed_retry` (1h) ·
`health_monitor` (5m). Each records metrics to `job_metrics`.

### Future scalability (`repositories.py`)

`PerfumeRepository` / `VectorRepository` / `RelationshipRepository` Protocols hide
SQLite/Qdrant. Swap to PostgreSQL or Qdrant Server by writing new adapters and
changing the factory — no caller changes.

### Full catalog crawl

`POST /admin/crawl/full` walks every A-Z (+0) designer index page, lists each
brand's perfumes via the AJAX endpoint, and **scrapes concurrently** while
discovery feeds the queue. Deduplication is by **perfume id** (the `-<id>.html`
suffix), not URL string — seed URLs are lowercase, scraped ones Title-Case, so
id-matching is the only reliable key. Ids already in the catalog or queue are
skipped, so only the *missing* perfumes are fetched. Progress survives restarts
(the `scrape_targets` queue is persistent); watch it via `/health` →
`crawl_progress` + `crawl_active`. At ~8-12s/page the full catalog takes days.

## Crawler

Runs as in-process scheduled jobs (`scheduler.py`):
- `discover_catalog` (weekly) — AJAX per-brand listing → enqueue new perfume URLs
- `discover_new_releases` (daily)
- `scrape_batch` (every 30 min) — bounded, rate-limited fetch + parse + Qdrant sync

State lives in the `scrape_targets` queue (resumable, cache-once). Politeness:
~8-12s/page, backoff on block, max 3 attempts. Respect Fragrantica's ToS — keep it slow.

## Recommendation policy

Global catalog is the search space; shop inventory is a **presentation boost**, never a
hard filter. Budget/gender are soft signals. In-stock shop items with a strong scent
match (≥0.90) are floated to the top — scent quality is always ranked first.
