"""
Central configuration.

All tunables live here and are overridable via environment variables, so the
rest of the codebase never reads os.environ directly. Heavy/optional stages
(cross-encoder reranker, multi-iteration agentic loop) are gated by flags that
default OFF — they trade latency for quality and are opt-in per deployment.
"""
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    # --- Paths ---
    DATA_DIR: Path = _HERE / "data"
    DB_PATH: str = os.getenv("DB_PATH", str(_HERE / "data" / "perfumes.db"))
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", str(_HERE / "data" / "qdrant"))
    CSV_PATH: str = os.getenv("CSV_PATH", str(_HERE / "data" / "fra_cleaned.csv"))
    SHOP_DB: str = os.getenv(
        "SHOP_DB", str(_HERE.parent / "server" / "database" / "perfume_finder.db")
    )

    # --- Embeddings / vector store ---
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
    VECTOR_DIM: int = _int("VECTOR_DIM", 384)
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "perfumes")

    # --- LLM (OpenAI-compatible: LM Studio / Ollama) ---
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    LLM_MODEL: str | None = os.getenv("LLM_MODEL")  # None → auto-detect
    LLM_TIMEOUT: float = _float("LLM_TIMEOUT", 120.0)
    LLM_MAX_TOKENS: int = _int("LLM_MAX_TOKENS", 1000)

    # --- Retrieval pipeline ---
    DENSE_K: int = _int("DENSE_K", 30)      # candidates from Qdrant
    SPARSE_K: int = _int("SPARSE_K", 30)    # candidates from FTS5
    RRF_K: int = _int("RRF_K", 60)          # RRF constant
    SPARSE_WEIGHT: float = _float("SPARSE_WEIGHT", 0.5)  # FTS weight vs dense (1.0)
    DENSE_STRONG: float = _float("DENSE_STRONG", 0.52)   # top cosine ≥ this = scent-led
    FUSED_K: int = _int("FUSED_K", 20)      # kept after fusion (rerank input)
    FINAL_K: int = _int("FINAL_K", 5)       # returned to the user

    # --- Composite reranker (query-aware recommendation score) ---
    # Deterministic post-fusion ranking: reorders the retrieved pool by a
    # recommendation score, not just the retrieval score. Feature-flagged so the
    # eval harness can A/B it and it can be rolled back instantly.
    ENABLE_RERANK: bool = _bool("ENABLE_RERANK", True)
    RERANK_POOL: int = _int("RERANK_POOL", 20)      # candidates scored per query
    MMR_LAMBDA: float = _float("MMR_LAMBDA", 0.7)    # diversity: 1.0=off, lower=more diverse
    MMR_BRAND_SIM: float = _float("MMR_BRAND_SIM", 0.25)  # same-brand adds to redundancy
    EXCLUDE_PENALTY: float = _float("EXCLUDE_PENALTY", 0.25)  # multiplier when a stated exclusion is hit

    # Base feature weights. Backbone (semantic·accord·occasion·season) intentionally
    # dominates the modifiers (approval·performance·price) so a popular-but-wrong
    # perfume can never outrank a well-fitting less-famous one. availability &
    # mass_appeal stay metadata-only in v1 (weight 0) until the benchmark earns them.
    RANK_WEIGHTS: dict = {
        "semantic": 1.0, "accord_match": 1.0, "occasion_fit": 0.6, "season_fit": 0.6,
        "approval": 0.35, "performance": 0.25, "price_fit": 0.30, "uniqueness": 0.0,
    }
    # Query-aware boosts, added to the base weight when the query asks for it.
    RANK_BOOSTS: dict = {
        "occasion": 0.4, "season": 0.3, "price": 0.4, "performance": 0.3,
        "unique": 0.6, "popular": 0.25,
    }

    # --- Optional heavy stages (default OFF — opt in when latency allows) ---
    ENABLE_CROSS_ENCODER: bool = _bool("ENABLE_CROSS_ENCODER", False)
    CROSS_ENCODER_MODEL: str = os.getenv("CROSS_ENCODER_MODEL", "BAAI/bge-reranker-v2-m3")
    ENABLE_AGENTIC: bool = _bool("ENABLE_AGENTIC", False)
    AGENT_MAX_TOOL_CALLS: int = _int("AGENT_MAX_TOOL_CALLS", 4)
    AGENT_MAX_ITERATIONS: int = _int("AGENT_MAX_ITERATIONS", 3)

    # Catalog-wide Playwright enrichment worker — OFF by default because headed
    # mode pops a browser window. Flip on to auto-harvest box/votes over time.
    ENABLE_ENRICHMENT_WORKER: bool = _bool("ENABLE_ENRICHMENT_WORKER", False)
    ENRICHMENT_BATCH: int = _int("ENRICHMENT_BATCH", 3)
    REL_BUILD_PAGE: int = _int("REL_BUILD_PAGE", 150)

    # --- Inventory presentation ---
    STRONG_MATCH: float = _float("STRONG_MATCH", 0.90)

    # --- Playwright (Stage-2 fallback for JS-rendered content) ---
    ENABLE_PLAYWRIGHT: bool = _bool("ENABLE_PLAYWRIGHT", True)  # used only if installed
    # Fragrantica's Cloudflare challenge blocks headless Chromium, so default to
    # headed — a real window auto-solves the JS challenge. Set true on a host with
    # a working headless-evasion setup.
    PLAYWRIGHT_HEADLESS: bool = _bool("PLAYWRIGHT_HEADLESS", False)
    # Let the bulk crawler auto-fall-back to Playwright? OFF by default — headed
    # windows during a long crawl are intrusive and fragile. Explicit /admin/enrich
    # still uses Playwright regardless.
    ENABLE_CRAWL_PLAYWRIGHT: bool = _bool("ENABLE_CRAWL_PLAYWRIGHT", False)
    PLAYWRIGHT_TIMEOUT_MS: int = _int("PLAYWRIGHT_TIMEOUT_MS", 30000)
    PLAYWRIGHT_PROFILE: str = os.getenv(
        "PLAYWRIGHT_PROFILE", str(_HERE / "data" / "pw_profile"))

    # --- Crawler ---
    SCRAPE_DELAY_MIN: float = _float("SCRAPE_DELAY_MIN", 2.5)
    SCRAPE_DELAY_MAX: float = _float("SCRAPE_DELAY_MAX", 4.5)
    SCRAPE_BACKOFF_MIN: float = _float("SCRAPE_BACKOFF_MIN", 20.0)
    SCRAPE_BACKOFF_MAX: float = _float("SCRAPE_BACKOFF_MAX", 30.0)
    SCRAPE_BATCH_SIZE: int = _int("SCRAPE_BATCH_SIZE", 40)
    SCRAPE_MAX_ATTEMPTS: int = _int("SCRAPE_MAX_ATTEMPTS", 3)


settings = Settings()
