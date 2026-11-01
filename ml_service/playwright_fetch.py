"""
Stage-2 crawler: Playwright (headless Chromium) for JS-rendered Fragrantica
content that curl_cffi can't see — the "reminds me of" box and vote charts.

Design:
  - Optional dependency. If playwright isn't installed, every call returns None
    and logs once — the system stays fully functional offline / Stage-1 only.
  - One persistent context (a size-1 browser pool guarded by a lock) reused across
    requests, so the Cloudflare clearance cookie and session persist between calls
    (user_data_dir). Sequential use matches our politeness model.
  - Request interception blocks images/CSS/fonts/media → faster, lighter renders.
  - Exponential backoff with retries; failures never crash the caller.

Progress/resume is unchanged — the crawler still drives everything from the
SQLite scrape_targets queue.
"""
import asyncio
import logging

from settings import settings

log = logging.getLogger("playwright")

_pw = None
_ctx = None
_lock = asyncio.Lock()
_warned = False
# Block only heavy media — keep CSS/fonts so the Cloudflare JS challenge renders
# and auto-solves normally.
_BLOCK = {"image", "media"}


def available() -> bool:
    if not settings.ENABLE_PLAYWRIGHT:
        return False
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


async def _block_route(route):
    if route.request.resource_type in _BLOCK:
        await route.abort()
    else:
        await route.continue_()


async def _ensure_context():
    """Lazily launch the persistent browser context (the size-1 pool)."""
    global _pw, _ctx, _warned
    if _ctx is not None:
        return _ctx
    if not available():
        if not _warned:
            log.warning("Playwright not available — Stage-2 rendering disabled "
                        "(install: pip install playwright && playwright install chromium)")
            _warned = True
        return None
    from playwright.async_api import async_playwright
    _pw = await async_playwright().start()
    _ctx = await _pw.chromium.launch_persistent_context(
        settings.PLAYWRIGHT_PROFILE,
        headless=settings.PLAYWRIGHT_HEADLESS,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        viewport={"width": 1280, "height": 900},
    )
    await _ctx.route("**/*", _block_route)
    log.info("Playwright context started (headless=%s)", settings.PLAYWRIGHT_HEADLESS)
    return _ctx


async def _reset_context() -> None:
    """Drop a dead/closed context so the next call re-launches a fresh browser."""
    global _ctx
    try:
        if _ctx is not None:
            await _ctx.close()
    except Exception:
        pass
    _ctx = None


async def render_html(url: str, wait_selector: str | None = None,
                      retries: int = 2) -> str | None:
    """Render a page and return its HTML after JS executes. None on failure.

    Resilient to a closed browser (e.g. the user closing the window): on any
    error the context is reset and re-launched on the next attempt, and nothing
    propagates to the caller — so a dead browser can never crash the service."""
    async with _lock:
        for attempt in range(retries + 1):
            ctx = await _ensure_context()
            if ctx is None:
                return None
            page = None
            try:
                page = await ctx.new_page()
                await page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT_MS,
                                wait_until="domcontentloaded")
                # Wait out the Cloudflare interstitial (a real browser auto-solves it).
                for _ in range(20):
                    if "just a moment" not in (await page.title()).lower():
                        break
                    await page.wait_for_timeout(1000)
                # Scroll to trigger lazy-loaded sections (the similar box, votes).
                for y in range(0, 12000, 1500):
                    await page.evaluate(f"window.scrollTo(0, {y})")
                    await page.wait_for_timeout(300)
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=10000)
                    except Exception:
                        pass  # component may be empty for this perfume — that's fine
                return await page.content()
            except Exception as e:
                log.warning("render failed (attempt %d) %s: %s", attempt + 1, url, e)
                await _reset_context()                 # browser may be dead — rebuild
                await asyncio.sleep(3 * (2 ** attempt))  # exponential backoff
            finally:
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
    return None


async def shutdown() -> None:
    global _ctx, _pw
    try:
        if _ctx is not None:
            await _ctx.close()
        if _pw is not None:
            await _pw.stop()
    except Exception:
        pass
    finally:
        _ctx = _pw = None
