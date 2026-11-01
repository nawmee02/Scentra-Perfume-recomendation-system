"""
Connectivity guard (Gap 9 — offline-first).

A cheap, cached TCP probe. Only network-dependent work (the Fragrantica crawler
and Playwright enrichment) consults this; everything local — SQLite, FTS5,
Qdrant, the embedding model, and the LLM (LM Studio is localhost) — keeps working
with no internet. When offline, crawler jobs pause instead of burning retries.
"""
import socket
import time
import logging

log = logging.getLogger("net")

_TTL = 30.0          # seconds to cache the verdict
_last_check = 0.0
_online = True
_PROBES = [("1.1.1.1", 443), ("8.8.8.8", 53)]


def is_online(timeout: float = 2.0) -> bool:
    global _last_check, _online
    now = time.monotonic()
    if now - _last_check < _TTL:
        return _online

    _last_check = now
    was = _online
    for host, port in _PROBES:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                _online = True
                break
        except OSError:
            _online = False

    if was and not _online:
        log.warning("Network is down — crawler/enrichment paused; search & LLM continue")
    elif not was and _online:
        log.info("Network is back — crawler resumes")
    return _online
