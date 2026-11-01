"""
Repository layer (Gap 10 — future scalability).

Protocols hide the storage implementation so business logic depends on interfaces,
not on SQLite/Qdrant specifics. Today the adapters delegate to the existing
db.py / qdrant_store.py; swapping to PostgreSQL or a remote Qdrant later means
writing new adapters and changing the factory below — no caller changes.

Adoption is incremental: new code (and the /perfume endpoint) goes through the
repos; existing hot paths can migrate over time.
"""
from typing import Protocol, runtime_checkable

import db
import qdrant_store


# --------------------------------------------------------------------------- #
# Interfaces
# --------------------------------------------------------------------------- #

@runtime_checkable
class PerfumeRepository(Protocol):
    def get(self, perfume_id: int) -> dict | None: ...
    def get_by_frag_id(self, fid: str) -> dict | None: ...
    def upsert(self, record: dict) -> None: ...
    def count(self) -> int: ...
    def search_keyword(self, query: str, limit: int = 30) -> list[dict]: ...
    def by_perfumer(self, perfumer: str, exclude_id: int | None, limit: int) -> list[dict]: ...


@runtime_checkable
class VectorRepository(Protocol):
    def search(self, query_text: str, limit: int = 20) -> list[dict]: ...
    def find_by_name(self, name: str, brand: str = "") -> dict | None: ...
    def count(self) -> int: ...


@runtime_checkable
class RelationshipRepository(Protocol):
    def add(self, src_frag_id: str, dst_frag_id: str, rel_type: str,
            confidence: float, source: str) -> None: ...
    def get(self, src_frag_id: str, rel_type: str | None = None,
            limit: int = 20) -> list[dict]: ...
    def count(self) -> int: ...


# --------------------------------------------------------------------------- #
# SQLite / Qdrant adapters (delegate to existing modules)
# --------------------------------------------------------------------------- #

class SqlitePerfumeRepository:
    def get(self, perfume_id: int) -> dict | None:
        return db.get_by_id(perfume_id)

    def get_by_frag_id(self, fid: str) -> dict | None:
        return db.get_by_frag_id(fid)

    def upsert(self, record: dict) -> None:
        db.upsert_perfume(record)

    def count(self) -> int:
        return db.count_perfumes()

    def search_keyword(self, query: str, limit: int = 30) -> list[dict]:
        return db.search_fts(query, limit)

    def by_perfumer(self, perfumer: str, exclude_id: int | None, limit: int) -> list[dict]:
        return db.by_perfumer(perfumer, exclude_id, limit)


class QdrantVectorRepository:
    def search(self, query_text: str, limit: int = 20) -> list[dict]:
        return qdrant_store.search(query_text, limit)

    def find_by_name(self, name: str, brand: str = "") -> dict | None:
        return qdrant_store.find_by_name(name, brand)

    def count(self) -> int:
        return qdrant_store.count_points()


class SqliteRelationshipRepository:
    def add(self, src_frag_id: str, dst_frag_id: str, rel_type: str,
            confidence: float, source: str) -> None:
        db.add_relationship(src_frag_id, dst_frag_id, rel_type,
                            confidence=confidence, source=source)

    def get(self, src_frag_id: str, rel_type: str | None = None,
            limit: int = 20) -> list[dict]:
        return db.get_relationships(src_frag_id, rel_type, limit)

    def count(self) -> int:
        return db.count_relationships()


# --------------------------------------------------------------------------- #
# Factory — swap implementations here (e.g. Postgres / Qdrant Cloud) later.
# --------------------------------------------------------------------------- #

_perfume_repo: PerfumeRepository = SqlitePerfumeRepository()
_vector_repo: VectorRepository = QdrantVectorRepository()
_relationship_repo: RelationshipRepository = SqliteRelationshipRepository()


def get_perfume_repo() -> PerfumeRepository:
    return _perfume_repo


def get_vector_repo() -> VectorRepository:
    return _vector_repo


def get_relationship_repo() -> RelationshipRepository:
    return _relationship_repo
