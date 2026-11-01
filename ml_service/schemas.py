"""
Pydantic v2 request/response schemas for the public API.

Keeping these in one place (instead of inline in main.py) gives every endpoint a
typed contract and a single source for response shapes.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    budget: float | None = None
    gender: str | None = None
    # Composite reranker toggle for live A/B (None → settings.ENABLE_RERANK).
    rerank: bool | None = None
    # Optional regional context (Gap 10) — post-retrieval re-rank only.
    lat: float | None = None
    lon: float | None = None
    temp_c: float | None = None
    humidity: float | None = None


class ChatRequest(BaseModel):
    query: str
    k: int = 5
    lat: float | None = None
    lon: float | None = None
    temp_c: float | None = None
    humidity: float | None = None


class SimilarRequest(BaseModel):
    name: str
    brand: str = ""
    k: int = 5


class PriceRequest(BaseModel):
    name: str
    brand: str = ""


class AdminPerfume(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    brand: str


# --------------------------------------------------------------------------- #
# Shared result shapes
# --------------------------------------------------------------------------- #

class InventoryMatch(BaseModel):
    in_stock: bool = False
    price: float | None = None


class Perfume(BaseModel):
    """A retrieved perfume as returned to clients (superset; fields optional)."""
    model_config = ConfigDict(extra="allow")

    db_id: int | None = None
    name: str = ""
    brand: str = ""
    gender: str = ""
    year: int | None = None
    top_notes: str = ""
    middle_notes: str = ""
    base_notes: str = ""
    accords: list[str] = Field(default_factory=list)
    season: str = ""
    occasion: str = ""
    rating: float | None = None
    score: float | None = None
    in_inventory: bool = False
    in_stock: bool = False
    price: float | None = None


class Constraints(BaseModel):
    """Soft preferences extracted from a free-form query."""
    budget: float | None = None
    gender: str | None = None
    season: str | None = None


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #

class SearchResponse(BaseModel):
    recommendations: list[dict]


class ChatResponse(BaseModel):
    reply: str | None = None
    recommendations: list[dict] = Field(default_factory=list)
    intent: str = "search"
    constraints: dict = Field(default_factory=dict)
    llm_used: bool = False


class SimilarResponse(BaseModel):
    seed: dict | None = None
    similar: list[dict] = Field(default_factory=list)
    source: str = "vector"  # graph | vector | none


class PriceResponse(BaseModel):
    results: list[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str = "ok"
