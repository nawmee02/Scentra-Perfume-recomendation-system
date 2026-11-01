"""
Qdrant vector store + shared embedding model.

Reads perfume rows from SQLite, encodes their `build_text()` representation with
SentenceTransformer, and upserts vectors + payload into Qdrant. Search is pure
cosine similarity over the whole catalog — budget/gender/inventory are applied
later as soft signals, never as hard filters here.
"""
import os

# Force the HuggingFace stack onto PyTorch only. Without this, `transformers`
# auto-detects a globally-installed TensorFlow and tries to load its TF/Keras
# integration, which crashes on Keras 3. We only use torch, so opt out of TF/Flax.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import json
import asyncio
import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer

import db

log = logging.getLogger("qdrant_store")

QDRANT_PATH = os.path.join(os.path.dirname(__file__), "data", "qdrant")
COLLECTION = "perfumes"
MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
VECTOR_DIM = 384  # all-MiniLM-L6-v2

# Shared singletons
model: SentenceTransformer | None = None
client: QdrantClient | None = None


def get_model() -> SentenceTransformer:
    global model
    if model is None:
        log.info("Loading embedding model %s", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME)
    return model


def get_client() -> QdrantClient:
    global client
    if client is None:
        os.makedirs(QDRANT_PATH, exist_ok=True)
        client = QdrantClient(path=QDRANT_PATH)
    return client


def init_collection() -> None:
    c = get_client()
    existing = {col.name for col in c.get_collections().collections}
    if COLLECTION not in existing:
        c.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=VECTOR_DIM, distance=qm.Distance.COSINE),
        )
        log.info("Created Qdrant collection '%s'", COLLECTION)


def _accords_list(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    try:
        parsed = json.loads(raw)
        return [str(a) for a in parsed if a] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return [raw]


def build_text(p: dict) -> str:
    """Encoder input — the compiled, intrinsic knowledge document (never raw JSON)."""
    import knowledge
    return knowledge.compile_embedding_doc(p)


def payload(p: dict) -> dict:
    """Public: normalize a SQLite perfume row into the standard result shape
    (same shape dense search returns), so sparse-only hits merge cleanly."""
    return _payload(p)


def _payload(p: dict) -> dict:
    """Stored alongside each vector. Includes lowercased keys for exact matching."""
    return {
        "db_id": p["id"],
        "name": p.get("name") or "",
        "brand": p.get("brand") or "",
        "name_lc": (p.get("name") or "").lower(),
        "brand_lc": (p.get("brand") or "").lower(),
        "gender_lc": (p.get("gender") or "").lower(),
        "year": p.get("year"),
        "gender": p.get("gender") or "",
        "top_notes": p.get("top_notes") or "",
        "middle_notes": p.get("middle_notes") or "",
        "base_notes": p.get("base_notes") or "",
        "accords": _accords_list(p.get("accords")),
        "season": p.get("season") or "",
        "occasion": p.get("occasion") or "",
        "longevity": p.get("longevity") or "",
        "sillage": p.get("sillage") or "",
        "rating": p.get("rating"),
        "rating_count": p.get("rating_count"),
        "in_inventory": bool(p.get("in_inventory")),
        "in_stock": bool(p.get("in_stock")),
        "price": p.get("price"),
        "sizes": _accords_list(p.get("sizes")),
        "image_url": p.get("image_url") or "",
        "new_release": bool(p.get("new_release")),
        "url": p.get("url") or "",
    }


async def sync_unsynced(batch_size: int = 512) -> int:
    """
    Encode + upsert all SQLite rows with qdrant_synced = 0.

    Encoding is CPU-bound, so it runs in a worker thread to keep the event loop
    responsive. Returns the number of perfumes synced.
    """
    m = get_model()
    c = get_client()
    init_collection()

    total = 0
    while True:
        rows = db.get_unsynced(limit=batch_size)
        if not rows:
            break

        texts = [build_text(r) for r in rows]
        vectors = await asyncio.to_thread(
            m.encode, texts, convert_to_numpy=True, normalize_embeddings=True
        )

        points = [
            qm.PointStruct(id=int(r["id"]), vector=vectors[i].tolist(), payload=_payload(r))
            for i, r in enumerate(rows)
        ]
        c.upsert(collection_name=COLLECTION, points=points)
        db.mark_synced([int(r["id"]) for r in rows])
        # Stamp embedding versioning so future schema bumps regenerate only stale rows.
        import knowledge
        for r in rows:
            db.set_embedding_meta(int(r["id"]), knowledge.KNOWLEDGE_SCHEMA_VERSION,
                                  MODEL_NAME, knowledge.content_hash(r))
        total += len(rows)
        log.info("Synced %d perfumes to Qdrant (running total %d)", len(rows), total)

        if len(rows) < batch_size:
            break
    return total


def count_points() -> int:
    try:
        return get_client().count(collection_name=COLLECTION).count
    except Exception:
        return 0


from functools import lru_cache

@lru_cache(maxsize=1024)
def _encode_query_cached(text: str) -> tuple:
    arr = get_model().encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
    return tuple(float(x) for x in arr)


def _encode_query(text: str):
    return list(_encode_query_cached((text or "").strip().lower()))


def search(query_text: str, limit: int = 20) -> list[dict]:
    """Pure cosine search over the whole catalog. No hard filters."""
    vector = _encode_query(query_text)
    hits = get_client().query_points(
        collection_name=COLLECTION,
        query=vector if isinstance(vector, list) else vector.tolist(),
        limit=limit,
        with_payload=True,
    ).points
    results = []
    for h in hits:
        rec = dict(h.payload)
        rec["score"] = float(h.score)
        results.append(rec)
    return results


def find_by_name(name: str, brand: str = "") -> dict | None:
    """Find one perfume by (lowercased) name, optionally constrained by brand."""
    must = [qm.FieldCondition(key="name_lc", match=qm.MatchValue(value=name.lower()))]
    if brand:
        must.append(qm.FieldCondition(key="brand_lc", match=qm.MatchValue(value=brand.lower())))
    hits = get_client().query_points(
        collection_name=COLLECTION,
        query_filter=qm.Filter(must=must),
        limit=1,
        with_payload=True,
        with_vectors=True,
    ).points
    if not hits:
        return None
    rec = dict(hits[0].payload)
    rec["_id"] = hits[0].id
    rec["_vector"] = hits[0].vector
    return rec


def search_by_vector(vector, limit: int = 6, exclude_id: int | None = None) -> list[dict]:
    hits = get_client().query_points(
        collection_name=COLLECTION,
        query=vector if isinstance(vector, list) else (vector.tolist() if hasattr(vector, 'tolist') else list(vector)),
        limit=limit + (1 if exclude_id is not None else 0),
        with_payload=True,
    ).points
    results = []
    for h in hits:
        if exclude_id is not None and h.id == exclude_id:
            continue
        rec = dict(h.payload)
        rec["score"] = float(h.score)
        results.append(rec)
    return results[:limit]
