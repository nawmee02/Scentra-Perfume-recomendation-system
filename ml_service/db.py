"""
SQLite master database — single source of truth.

Holds the full fragrance catalog (seed CSV + crawled Fragrantica data), shop
inventory flags, and the crawl queue (scrape_targets). Qdrant is rebuilt/synced
from this table via the `qdrant_synced` flag.
"""
import os
import re
import json
import sqlite3
import threading
from datetime import datetime

# Fragrantica perfume URLs end in '-<id>.html'. That numeric id is the canonical
# identifier — the slug casing varies (lowercase in the seed CSV, Title-Case when
# scraped), so we dedup on the id, not the URL string.
_FRAG_ID_RE = re.compile(r"-(\d+)\.html", re.I)


def frag_id(url: str | None) -> str | None:
    if not url:
        return None
    m = _FRAG_ID_RE.search(url)
    return m.group(1) if m else None

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "perfumes.db")

# Columns that upsert_perfume is allowed to write. Order is not significant.
PERFUME_COLUMNS = [
    "name", "brand", "year", "gender",
    "top_notes", "middle_notes", "base_notes",
    "accords", "season", "occasion", "description",
    "rating", "rating_count", "country", "perfumer1", "perfumer2",
    "longevity", "sillage",
    # inventory
    "in_inventory", "price", "original_price", "sizes", "image_url",
    "in_stock", "discount",
    # metadata
    "source", "new_release", "url",
]

# A single connection guarded by a lock. SQLite handles one writer at a time and
# the service is single-process; the lock keeps the scheduler thread and request
# handlers from interleaving writes.
_conn = None
_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        try:
            _conn.execute("PRAGMA journal_mode = WAL")
            _conn.execute("PRAGMA synchronous = NORMAL")
            _conn.execute("PRAGMA cache_size = -64000")
        except sqlite3.Error:
            pass
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


def init_db():
    conn = get_connection()
    with _lock:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perfumes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                brand           TEXT NOT NULL,
                year            INTEGER,
                gender          TEXT,
                top_notes       TEXT,
                middle_notes    TEXT,
                base_notes      TEXT,
                accords         TEXT,            -- JSON array
                season          TEXT,
                occasion        TEXT,
                description     TEXT,
                rating          REAL,
                rating_count    INTEGER,
                country         TEXT,
                perfumer1       TEXT,
                perfumer2       TEXT,
                longevity       TEXT,
                sillage         TEXT,
                in_inventory    INTEGER DEFAULT 0,
                price           REAL,
                original_price  REAL,
                sizes           TEXT,            -- JSON array
                image_url       TEXT,
                in_stock        INTEGER DEFAULT 0,
                discount        INTEGER DEFAULT 0,
                source          TEXT DEFAULT 'csv',
                new_release     INTEGER DEFAULT 0,
                url             TEXT,
                qdrant_synced   INTEGER DEFAULT 0,
                scraped_at      DATETIME,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, brand)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_brand ON perfumes(brand)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_inventory ON perfumes(in_inventory)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_synced ON perfumes(qdrant_synced)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_new ON perfumes(new_release)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_targets (
                url           TEXT PRIMARY KEY,
                brand         TEXT,
                status        TEXT DEFAULT 'pending',   -- pending | done | failed
                attempts      INTEGER DEFAULT 0,
                is_new        INTEGER DEFAULT 0,        -- came from the new-releases page
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                scraped_at    DATETIME,
                last_error    TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scrape_status ON scrape_targets(status)")
        # Migration for DBs created before is_new existed.
        try:
            conn.execute("ALTER TABLE scrape_targets ADD COLUMN is_new INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # FTS5 sparse index — rowid mirrors perfumes.id. Standalone (own storage)
        # so it's robust to the COALESCE-upsert flow; kept current via rebuild_fts().
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS perfumes_fts USING fts5(
                name, brand, notes, accords, perfumers,
                tokenize = 'porter unicode61'
            )
        """)

        # Knowledge graph: explicit, non-embedding relationships between perfumes,
        # keyed by Fragrantica id so edges can exist before the target is scraped.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                src_frag_id  TEXT NOT NULL,
                dst_frag_id  TEXT NOT NULL,
                rel_type     TEXT NOT NULL,   -- similar_to | clone_of | flanker_of |
                                              -- shares_perfumer | same_collection |
                                              -- reformulation_of | inspired_by | discontinued
                weight       INTEGER DEFAULT 0,   -- vote count / ordering proxy
                mirrored     INTEGER DEFAULT 0,
                dst_url      TEXT,
                dst_name     TEXT,
                PRIMARY KEY (src_frag_id, dst_frag_id, rel_type)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_src ON relationships(src_frag_id, rel_type)")
        conn.commit()

    # Apply additive, versioned migrations (relationship evidence, consensus
    # votes, embedding versioning). Idempotent — safe on every startup.
    import migrations
    with _lock:
        migrations.run(conn)


# --------------------------------------------------------------------------- #
# Perfume writes / reads
# --------------------------------------------------------------------------- #

def upsert_perfume(record: dict) -> None:
    """
    INSERT a perfume or enrich an existing one (matched on name+brand).

    Uses COALESCE(excluded.col, perfumes.col) so a partial write (e.g. a scrape
    that only found notes, or an admin call that only sets price) never wipes
    data already present. Any write marks the row unsynced so Qdrant picks it up.
    """
    cols = [c for c in PERFUME_COLUMNS if c in record and record[c] is not None]
    if "name" not in cols or "brand" not in cols:
        raise ValueError("upsert_perfume requires 'name' and 'brand'")

    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(
        f"{c} = COALESCE(excluded.{c}, perfumes.{c})"
        for c in cols if c not in ("name", "brand")
    )
    updates = (updates + ", " if updates else "") + \
        "qdrant_synced = 0, updated_at = CURRENT_TIMESTAMP"

    sql = (
        f"INSERT INTO perfumes ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(name, brand) DO UPDATE SET {updates}"
    )
    conn = get_connection()
    with _lock:
        conn.execute(sql, [record[c] for c in cols])
        conn.commit()


def count_perfumes() -> int:
    row = get_connection().execute("SELECT COUNT(*) AS c FROM perfumes").fetchone()
    return row["c"]


def get_unsynced(limit: int = 2000) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE qdrant_synced = 0 LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_synced(ids: list[int]) -> None:
    if not ids:
        return
    conn = get_connection()
    with _lock:
        conn.executemany(
            "UPDATE perfumes SET qdrant_synced = 1 WHERE id = ?",
            [(i,) for i in ids],
        )
        conn.commit()


def get_inventory() -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE in_inventory = 1"
    ).fetchall()
    return [dict(r) for r in rows]


def search_by_name_like(token: str, limit: int = 60) -> list[dict]:
    """Coarse name match for fragrance resolution; most-reviewed first."""
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE lower(name) LIKE ? "
        "ORDER BY COALESCE(rating_count, 0) DESC LIMIT ?",
        (f"%{token.lower()}%", limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(perfume_id: int) -> dict | None:
    r = get_connection().execute(
        "SELECT * FROM perfumes WHERE id = ?", (perfume_id,)
    ).fetchone()
    return dict(r) if r else None


def get_by_frag_id(fid: str) -> dict | None:
    """Resolve a Fragrantica id to a catalog row (matches the URL suffix)."""
    if not fid:
        return None
    r = get_connection().execute(
        "SELECT * FROM perfumes WHERE url LIKE ? LIMIT 1", (f"%-{fid}.html",)
    ).fetchone()
    return dict(r) if r else None


def by_perfumer(perfumer: str, exclude_id: int | None = None, limit: int = 20) -> list[dict]:
    """Other perfumes by the same perfumer (most-reviewed first)."""
    if not perfumer or perfumer.strip().lower() == "unknown":
        return []
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE (perfumer1 = ? OR perfumer2 = ?) AND id != ? "
        "ORDER BY COALESCE(rating_count, 0) DESC LIMIT ?",
        (perfumer, perfumer, exclude_id or -1, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# FTS5 sparse retrieval
# --------------------------------------------------------------------------- #

_FTS_WORD = re.compile(r"[A-Za-z0-9]+")


def _fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression (OR over quoted terms)."""
    words = [w for w in _FTS_WORD.findall((text or "").lower()) if len(w) > 1]
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words))


def count_fts() -> int:
    try:
        return get_connection().execute("SELECT COUNT(*) AS c FROM perfumes_fts").fetchone()["c"]
    except sqlite3.Error:
        return 0


def rebuild_fts() -> int:
    """Repopulate the FTS index from perfumes. Cheap full rebuild (~1-2s/24k)."""
    conn = get_connection()
    with _lock:
        conn.execute("DELETE FROM perfumes_fts")
        conn.execute("""
            INSERT INTO perfumes_fts(rowid, name, brand, notes, accords, perfumers)
            SELECT id,
                   COALESCE(name, ''),
                   COALESCE(brand, ''),
                   TRIM(COALESCE(top_notes,'')||' '||COALESCE(middle_notes,'')||' '||COALESCE(base_notes,'')),
                   COALESCE(accords, ''),
                   TRIM(COALESCE(perfumer1,'')||' '||COALESCE(perfumer2,''))
            FROM perfumes
        """)
        conn.commit()
    return count_fts()


def search_fts(query: str, limit: int = 30) -> list[dict]:
    """Sparse keyword retrieval (bm25-ranked). Returns perfume rows, best first."""
    match = _fts_query(query)
    if not match:
        return []
    try:
        rows = get_connection().execute(
            "SELECT p.*, bm25(perfumes_fts) AS bm25 "
            "FROM perfumes_fts JOIN perfumes p ON p.id = perfumes_fts.rowid "
            "WHERE perfumes_fts MATCH ? ORDER BY bm25 LIMIT ?",
            (match, limit),
        ).fetchall()
    except sqlite3.Error:
        return []
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Relationship graph
# --------------------------------------------------------------------------- #

def add_relationship(src_frag_id: str, dst_frag_id: str, rel_type: str,
                     confidence: float = 0.0, source: str = "",
                     weight: int = 0, mirrored: int = 0,
                     dst_url: str | None = None, dst_name: str | None = None) -> None:
    """Insert or strengthen a relationship edge.

    Confidence is merged with noisy-OR — `1 - (1-old)*(1-new)` — so independent
    evidence accumulates and a weaker source can never lower a stronger edge.
    `sources` keeps the contributing source ids; `discovered_at` is first-seen.
    """
    if not src_frag_id or not dst_frag_id or src_frag_id == dst_frag_id:
        return
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO relationships "
            "(src_frag_id, dst_frag_id, rel_type, confidence, sources, "
            " weight, mirrored, dst_url, dst_name, discovered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(src_frag_id, dst_frag_id, rel_type) DO UPDATE SET "
            "  confidence = 1.0 - (1.0 - relationships.confidence) * (1.0 - excluded.confidence), "
            "  weight = MAX(relationships.weight, excluded.weight), "
            "  dst_url = COALESCE(excluded.dst_url, relationships.dst_url), "
            "  dst_name = COALESCE(excluded.dst_name, relationships.dst_name), "
            "  sources = CASE "
            "     WHEN excluded.sources IS NULL OR excluded.sources = '' THEN relationships.sources "
            "     WHEN relationships.sources IS NULL OR relationships.sources = '' THEN excluded.sources "
            "     WHEN instr(','||relationships.sources||',', ','||excluded.sources||',') > 0 THEN relationships.sources "
            "     ELSE relationships.sources || ',' || excluded.sources END",
            (src_frag_id, dst_frag_id, rel_type, float(confidence), source or None,
             weight, mirrored, dst_url, dst_name),
        )
        conn.commit()


# --------------------------------------------------------------------------- #
# Embedding versioning
# --------------------------------------------------------------------------- #

def set_votes(perfume_id: int, longevity: dict | None = None,
              sillage: dict | None = None, gender: dict | None = None) -> None:
    """Store community vote distributions (JSON) for a perfume (Gap 4)."""
    sets, params = [], []
    for col, val in (("longevity_votes", longevity), ("sillage_votes", sillage),
                     ("gender_votes", gender)):
        if val:
            sets.append(f"{col} = ?")
            params.append(json.dumps(val))
    if not sets:
        return
    # Votes feed the embedding doc (performance consensus) — re-embed on change.
    sets.append("qdrant_synced = 0")
    params.append(perfume_id)
    conn = get_connection()
    with _lock:
        conn.execute(f"UPDATE perfumes SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()


def set_embedding_meta(perfume_id: int, schema_version: str, model: str,
                       content_hash: str) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            "UPDATE perfumes SET embedding_schema_version = ?, embedding_model = ?, "
            "embedding_hash = ?, embedding_created_at = CURRENT_TIMESTAMP WHERE id = ?",
            (schema_version, model, content_hash, perfume_id),
        )
        conn.commit()


def mark_stale_embeddings(schema_version: str) -> int:
    """Flag rows whose embedding predates the current schema for re-sync.
    Targeted regeneration — never a full rebuild unless every row is stale."""
    conn = get_connection()
    with _lock:
        cur = conn.execute(
            "UPDATE perfumes SET qdrant_synced = 0 "
            "WHERE embedding_schema_version IS NULL OR embedding_schema_version != ?",
            (schema_version,),
        )
        conn.commit()
        return cur.rowcount


def iter_perfumes(offset: int = 0, limit: int = 500) -> list[dict]:
    """Page through the catalog (for background workers like relationship build)."""
    rows = get_connection().execute(
        "SELECT * FROM perfumes ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Background-worker metrics + state (Gap 7)
# --------------------------------------------------------------------------- #

def record_job(job: str, status: str, items: int = 0,
               duration_ms: int = 0, error: str | None = None) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO job_metrics "
            "(job, last_run, last_status, last_items, last_duration_ms, last_error, "
            " runs_total, items_total) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, 1, ?) "
            "ON CONFLICT(job) DO UPDATE SET last_run=CURRENT_TIMESTAMP, "
            " last_status=excluded.last_status, last_items=excluded.last_items, "
            " last_duration_ms=excluded.last_duration_ms, last_error=excluded.last_error, "
            " runs_total=job_metrics.runs_total+1, "
            " items_total=job_metrics.items_total+excluded.items_total",
            (job, status, items, duration_ms, error, items),
        )
        conn.commit()


def get_job_metrics() -> list[dict]:
    return [dict(r) for r in get_connection().execute(
        "SELECT * FROM job_metrics ORDER BY last_run DESC")]


def get_state(key: str, default: str | None = None) -> str | None:
    r = get_connection().execute(
        "SELECT value FROM worker_state WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else default


def set_state(key: str, value: str) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO worker_state(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        conn.commit()


def top_unenriched(limit: int = 5) -> list[dict]:
    """Most-popular perfumes not yet Playwright-enriched (have a URL)."""
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE enriched_at IS NULL AND url IS NOT NULL "
        "ORDER BY COALESCE(rating_count, 0) DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def set_inferred_season(perfume_id: int, season: str) -> None:
    """Store inferred season separately; mark stale so the embedding doc updates."""
    conn = get_connection()
    with _lock:
        conn.execute(
            "UPDATE perfumes SET inferred_season=?, qdrant_synced=0 WHERE id=?",
            (season, perfume_id))
        conn.commit()


def mark_enriched(perfume_id: int) -> None:
    conn = get_connection()
    with _lock:
        conn.execute("UPDATE perfumes SET enriched_at=CURRENT_TIMESTAMP WHERE id=?",
                     (perfume_id,))
        conn.commit()


def reset_failed_targets() -> int:
    """Give failed crawl targets another chance (failed_retry worker)."""
    conn = get_connection()
    with _lock:
        cur = conn.execute(
            "UPDATE scrape_targets SET status='pending', attempts=0, last_error=NULL "
            "WHERE status='failed'")
        conn.commit()
        return cur.rowcount


def add_relationships_bulk(edges: list[tuple]) -> int:
    """Batch UPSERT of edges in one transaction (for structural inference).

    Each edge = (src_frag_id, dst_frag_id, rel_type, confidence, source,
    dst_url, dst_name). Same noisy-OR merge as add_relationship."""
    rows = [e for e in edges if e[0] and e[1] and e[0] != e[1]]
    if not rows:
        return 0
    conn = get_connection()
    with _lock:
        conn.executemany(
            "INSERT INTO relationships "
            "(src_frag_id, dst_frag_id, rel_type, confidence, sources, "
            " dst_url, dst_name, discovered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(src_frag_id, dst_frag_id, rel_type) DO UPDATE SET "
            "  confidence = 1.0 - (1.0 - relationships.confidence) * (1.0 - excluded.confidence), "
            "  dst_url = COALESCE(excluded.dst_url, relationships.dst_url), "
            "  dst_name = COALESCE(excluded.dst_name, relationships.dst_name), "
            "  sources = CASE "
            "     WHEN excluded.sources IS NULL OR excluded.sources='' THEN relationships.sources "
            "     WHEN relationships.sources IS NULL OR relationships.sources='' THEN excluded.sources "
            "     WHEN instr(','||relationships.sources||',', ','||excluded.sources||',')>0 THEN relationships.sources "
            "     ELSE relationships.sources||','||excluded.sources END",
            rows,
        )
        conn.commit()
    return len(rows)


def get_catalog_min() -> list[dict]:
    """Lightweight catalog rows for structural inference."""
    rows = get_connection().execute(
        "SELECT id, name, brand, url, year FROM perfumes WHERE url IS NOT NULL"
    ).fetchall()
    return [dict(r) for r in rows]


def cleanup_relationships() -> int:
    """Graph repair — drop self-edges and malformed rows. Returns rows removed."""
    conn = get_connection()
    with _lock:
        cur = conn.execute(
            "DELETE FROM relationships WHERE src_frag_id = dst_frag_id "
            "OR src_frag_id IS NULL OR dst_frag_id IS NULL OR rel_type IS NULL")
        conn.commit()
        return cur.rowcount


def get_relationships(src_frag_id: str, rel_type: str | None = None,
                      limit: int = 20) -> list[dict]:
    sql = "SELECT * FROM relationships WHERE src_frag_id = ?"
    params: list = [src_frag_id]
    if rel_type:
        sql += " AND rel_type = ?"
        params.append(rel_type)
    sql += " ORDER BY weight DESC, rowid ASC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in get_connection().execute(sql, params).fetchall()]


def count_relationships() -> int:
    return get_connection().execute(
        "SELECT COUNT(*) AS c FROM relationships"
    ).fetchone()["c"]


def count_inventory() -> int:
    row = get_connection().execute(
        "SELECT COUNT(*) AS c FROM perfumes WHERE in_inventory = 1"
    ).fetchone()
    return row["c"]


def get_new_releases(limit: int = 10) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM perfumes WHERE new_release = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Crawl queue (scrape_targets)
# --------------------------------------------------------------------------- #

def enqueue_url(url: str, brand: str | None = None, is_new: bool = False) -> None:
    conn = get_connection()
    with _lock:
        # If a URL is re-seen via the new-releases page, raise its is_new flag.
        conn.execute(
            "INSERT INTO scrape_targets (url, brand, is_new) VALUES (?, ?, ?) "
            "ON CONFLICT(url) DO UPDATE SET is_new = MAX(scrape_targets.is_new, excluded.is_new)",
            (url, brand, 1 if is_new else 0),
        )
        conn.commit()


def get_pending_targets(limit: int = 100) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM scrape_targets WHERE status = 'pending' AND attempts < 3 ORDER BY is_new DESC, attempts ASC, discovered_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_target_done(url: str) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            "UPDATE scrape_targets SET status='done', scraped_at=? WHERE url=?",
            (datetime.utcnow().isoformat(), url),
        )
        conn.commit()


def mark_target_failed(url: str, error: str) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            """UPDATE scrape_targets
               SET attempts = attempts + 1,
                   last_error = ?,
                   status = CASE WHEN attempts + 1 >= 3 THEN 'failed' ELSE 'pending' END
               WHERE url = ?""",
            (error[:500], url),
        )
        conn.commit()


def count_targets_by_status() -> dict:
    rows = get_connection().execute(
        "SELECT status, COUNT(*) AS c FROM scrape_targets GROUP BY status"
    ).fetchall()
    return {r["status"]: r["c"] for r in rows}


def existing_frag_ids() -> set[str]:
    """All perfume ids we already know — from the catalog and the crawl queue.

    Used by discovery to skip perfumes we already have or have already queued,
    regardless of URL-slug casing.
    """
    conn = get_connection()
    ids: set[str] = set()
    for table in ("perfumes", "scrape_targets"):
        for r in conn.execute(f"SELECT url FROM {table}"):
            fid = frag_id(r["url"])
            if fid:
                ids.add(fid)
    return ids
