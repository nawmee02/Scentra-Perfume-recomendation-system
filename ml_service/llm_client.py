"""
LLM client — OpenAI-compatible chat API.

Targets LM Studio's local server by default (http://localhost:1234/v1). The same
code works against any OpenAI-compatible endpoint (Ollama's /v1, llama.cpp, etc.)
by setting LLM_BASE_URL.

The loaded model is auto-detected from /v1/models so the user doesn't have to
hard-code a model id; override with LLM_MODEL if desired.

A cached availability probe keeps each request from paying the connection cost;
it resets on failure so the service recovers if the server starts later.
"""
import os
import logging

import httpx

log = logging.getLogger("llm")

LLM_BASE = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL_ENV = os.getenv("LLM_MODEL")  # optional explicit override

_available: bool | None = None
_resolved_model: str | None = None


def _model() -> str:
    return LLM_MODEL_ENV or _resolved_model or "local-model"


async def check_available(force: bool = False) -> bool:
    global _available, _resolved_model
    if _available is not None and not force:
        return _available
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{LLM_BASE}/models")
        if r.status_code != 200:
            _available = False
            return _available

        models = (r.json() or {}).get("data", [])
        # Exclude embedding models — they can't do chat/tool-calling. If only an
        # embedding model is loaded (common in LM Studio), treat chat as
        # unavailable so the agent uses the vector-search fallback cleanly.
        chat_models = [m for m in models if "embed" not in (m.get("id") or "").lower()]
        if LLM_MODEL_ENV:
            _available = True
        elif chat_models:
            _available = True
            _resolved_model = chat_models[0].get("id")
            log.info("LLM available; using chat model '%s'", _resolved_model)
        else:
            _available = False
            log.warning("LM Studio reachable but no chat model loaded (only embeddings) "
                        "— load a chat model (e.g. Qwen2.5-7B-Instruct) to enable /chat LLM")
    except Exception:
        _available = False
        log.warning("LLM unavailable at %s — using vector-search fallback", LLM_BASE)
    return _available


def is_available() -> bool | None:
    return _available


def mark_unavailable() -> None:
    global _available
    _available = False


async def _post(payload: dict, timeout: float) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{LLM_BASE}/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]


async def chat(messages: list[dict], tools: list[dict] | None = None,
               timeout: float = 120.0, max_tokens: int | None = None) -> dict:
    """
    One chat-completions round. Returns the assistant `message` dict
    (OpenAI shape: {role, content, tool_calls?}).

    LM Studio JIT-loads/unloads models, so the cached model id can go stale
    (500 "Model unloaded"). We retry once ONLY on an HTTP status error (re-
    resolving the model first). Timeouts are NOT retried — retrying a slow call
    just doubles the wait.
    """
    payload = {"model": _model(), "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    if max_tokens:
        payload["max_tokens"] = max_tokens
    try:
        return await _post(payload, timeout)
    except httpx.HTTPStatusError:
        await check_available(force=True)
        payload["model"] = _model()
        return await _post(payload, timeout)
