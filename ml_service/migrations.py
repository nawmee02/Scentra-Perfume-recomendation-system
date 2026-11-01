"""
Versioned, additive schema migrations.

Run on every startup after init_db(). Each migration is a list of idempotent
DDL statements (ADD COLUMN / CREATE TABLE IF NOT EXISTS) — never destructive, so
existing rows and API contracts are preserved. Applied versions are tracked in
schema_migrations; re-running is a no-op.

To evolve the schema, append a (version, name, statements) tuple — do not edit
already-applied migrations.
"""
import logging
import sqlite3

log = logging.getLogger("migrations")

# (version, name, [sql statements]) — append-only.
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "relationship_evidence", [
        "ALTER TABLE relationships ADD COLUMN confidence REAL DEFAULT 0",
        "ALTER TABLE relationships ADD COLUMN sources TEXT",
        "ALTER TABLE relationships ADD COLUMN discovered_at DATETIME",
    ]),
    (2, "consensus_votes", [
        # JSON vote distributions, e.g. {"long lasting": 120, "moderate": 80, ...}
        "ALTER TABLE perfumes ADD COLUMN longevity_votes TEXT",
        "ALTER TABLE perfumes ADD COLUMN sillage_votes TEXT",
        "ALTER TABLE perfumes ADD COLUMN gender_votes TEXT",
    ]),
    (3, "embedding_versioning", [
        "ALTER TABLE perfumes ADD COLUMN embedding_schema_version TEXT",
        "ALTER TABLE perfumes ADD COLUMN embedding_model TEXT",
        "ALTER TABLE perfumes ADD COLUMN embedding_hash TEXT",
        "ALTER TABLE perfumes ADD COLUMN embedding_created_at DATETIME",
    ]),
    (4, "worker_metrics", [
        "CREATE TABLE IF NOT EXISTS job_metrics ("
        " job TEXT PRIMARY KEY, last_run DATETIME, last_status TEXT,"
        " last_items INTEGER DEFAULT 0, last_duration_ms INTEGER DEFAULT 0,"
        " last_error TEXT, runs_total INTEGER DEFAULT 0, items_total INTEGER DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS worker_state (key TEXT PRIMARY KEY, value TEXT)",
        "ALTER TABLE perfumes ADD COLUMN enriched_at DATETIME",
    ]),
    (5, "inferred_season", [
        # Inferred seasonal suitability, stored separately from any crawled value.
        "ALTER TABLE perfumes ADD COLUMN inferred_season TEXT",
    ]),
]


def _applied(conn: sqlite3.Connection) -> set[int]:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def run(conn: sqlite3.Connection) -> int:
    """Apply all pending migrations. Returns the count applied this run."""
    done = _applied(conn)
    applied = 0
    for version, name, statements in MIGRATIONS:
        if version in done:
            continue
        for sql in statements:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as e:
                # Column/table already exists — safe to ignore (additive only).
                if "duplicate column" not in str(e).lower():
                    log.warning("migration %s: %s (%s)", version, e, sql)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
            (version, name),
        )
        conn.commit()
        applied += 1
        log.info("Applied migration %d (%s)", version, name)
    return applied
