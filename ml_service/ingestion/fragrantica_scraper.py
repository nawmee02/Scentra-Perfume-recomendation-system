"""
Fragrantica crawler.

Transport: curl_cffi with Chrome impersonation (passes Cloudflare's passive TLS
fingerprint check that plain `requests` fails). Discovery uses the AJAX
`simple.perfume.list` endpoint per designer; parsing relies on Fragrantica's
itemprop microdata + the `#83a6c4` performance-bar pattern, all present in the
static HTML (no JS / Playwright needed).

Selectors and the AJAX technique are re-implemented from the PerfumAPI reference
(github.com/seccaz/PerfumAPI), which carries no OSS license.

Politeness: bounded batches, randomized delays, backoff on block, cache-once via
the scrape_targets queue. This violates Fragrantica's ToS for community data, so
keep it slow and never re-fetch a completed URL.
"""
import re
import json
import random
import asyncio
import logging

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cffi
except ImportError:  # surfaces clearly if the dep is missing
    cffi = None

import db
import net
import qdrant_store
import playwright_fetch
from settings import settings
from ingestion.tagging import infer_season, infer_occasion

log = logging.getLogger("fragrantica")

BASE = "https://www.fragrantica.com"
DESIGNERS_URL = f"{BASE}/designers/"
NEW_RELEASES_URL = f"{BASE}/new-fragrances/"
AJAX_URL = f"{BASE}/scripts/server.php"  # simple.perfume.list endpoint

PERFUME_HREF = re.compile(r"/perfume/[^/\"']+/[^/\"']+\.html")
DESIGNER_HREF = re.compile(r"/designers/[^/\"']+\.html")
DESIGNER_ID = re.compile(r"/o\.(\d+)\.jpg")
LAUNCH_YEAR = re.compile(r"launched in (\d{4})")


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #

def _fetch(url: str, method: str = "GET", data=None) -> str | None:
    if cffi is None:
        log.error("curl_cffi not installed; cannot fetch %s", url)
        return None
    try:
        if method == "POST":
            r = cffi.post(url, data=data, impersonate="chrome", timeout=25)
        else:
            r = cffi.get(url, impersonate="chrome", timeout=25)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        log.warning("fetch failed %s: %s", url, e)
        return None


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

# Alphabetical designer index pages list every brand; '0' covers numeric names.
LETTER_PAGES = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0"]


def _abs(href: str) -> str:
    return href if href.startswith("http") else BASE + href


def _enqueue_new(url: str, brand: str | None, known: set[str], is_new: bool = False) -> int:
    """Enqueue only if this perfume id is not already known. Mutates `known`."""
    fid = db.frag_id(url)
    if not fid or fid in known:
        return 0
    known.add(fid)
    db.enqueue_url(url, brand, is_new=is_new)
    return 1


async def discover_catalog() -> int:
    """
    Full-catalog discovery, deduped by perfume id:
      for each A-Z (+0) designer index page →
        enqueue the perfume links printed on the page, then walk each brand's
        AJAX perfume list. Ids already in the catalog or the queue are skipped,
        so only the *missing* perfumes get queued.
    """
    if not net.is_online():
        log.info("discover_catalog: offline — skipping")
        return 0
    known = await asyncio.to_thread(db.existing_frag_ids)
    log.info("discover_catalog: %d ids already known", len(known))
    enqueued = 0

    for letter in LETTER_PAGES:
        html = await asyncio.to_thread(_fetch, f"{BASE}/designers/{letter}.html")
        await asyncio.sleep(random.uniform(8, 12))
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")

        for href in PERFUME_HREF.findall(html):
            enqueued += _enqueue_new(_abs(href), None, known)

        brand_urls = {_abs(a["href"]) for a in soup.find_all("a", href=DESIGNER_HREF)}
        for brand_url in brand_urls:
            enqueued += await _discover_brand(brand_url, known)
            await asyncio.sleep(random.uniform(8, 12))

        log.info("discover_catalog: letter %s done — %d new queued so far", letter, enqueued)

    log.info("discover_catalog: enqueued %d new perfume URLs", enqueued)
    return enqueued


async def _discover_brand(brand_url: str, known: set[str]) -> int:
    html = await asyncio.to_thread(_fetch, brand_url)
    if not html:
        return 0
    soup = BeautifulSoup(html, "lxml")

    # Extract designer_id from the og:image (/o.<id>.jpg) or inline script.
    designer_id = None
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        m = DESIGNER_ID.search(og["content"])
        if m:
            designer_id = m.group(1)
    if not designer_id:
        m = re.search(r"designer_id['\"]?\s*[:=]\s*['\"]?(\d+)", html)
        if m:
            designer_id = m.group(1)

    links: set[str] = set()
    if designer_id:
        form = f"action=simple.perfume.list&designer_id={designer_id}&mode=popular"
        ajax_html = await asyncio.to_thread(_fetch, AJAX_URL, "POST", form)
        if ajax_html:
            links.update(_abs(m) for m in PERFUME_HREF.findall(ajax_html))
    for a in soup.find_all("a", href=PERFUME_HREF):
        links.add(_abs(a["href"]))

    brand_name = brand_url.rsplit("/", 1)[-1].replace(".html", "").replace("-", " ")
    return sum(_enqueue_new(link, brand_name, known) for link in links)


async def discover_new_releases() -> int:
    html = await asyncio.to_thread(_fetch, NEW_RELEASES_URL)
    if not html:
        return 0
    soup = BeautifulSoup(html, "lxml")
    known = await asyncio.to_thread(db.existing_frag_ids)
    count = 0
    for a in soup.find_all("a", href=PERFUME_HREF):
        count += _enqueue_new(_abs(a["href"]), None, known, is_new=True)
    log.info("discover_new_releases: enqueued %d URLs", count)
    return count


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


def _clean_name(raw: str | None, brand: str | None) -> str | None:
    """Fragrantica titles are '<Perfume> <Brand> for <gender>'. Strip both."""
    if not raw:
        return raw
    n = raw.strip()
    # Drop a trailing 'for women/men/...' (space before 'for' may be missing).
    n = re.sub(r"\s*for\s+(women and men|women|men|unisex)\s*$", "", n, flags=re.I).strip()
    n = re.sub(r"(women and men|women|men)$", "", n).strip()
    if brand and n.lower().endswith(brand.lower()):
        n = n[: -len(brand)].strip()
    return n or raw


def _notes_from_anchors(container) -> str | None:
    notes = [a.get_text(strip=True)
             for a in container.find_all("a", href=re.compile(r"/notes/"))
             if a.get_text(strip=True)]
    return ", ".join(dict.fromkeys(notes)) if notes else None


def _parse_notes(soup) -> tuple[str | None, str | None, str | None]:
    """
    Notes live in custom <pyramid-level-new notes="top|middle|base"> elements,
    each containing /notes/ anchors. Some perfumes only have a flat note list
    (no pyramid) — fall back to all /notes/ anchors as top notes.
    """
    sections = {"top": None, "middle": None, "base": None}
    for lvl in soup.find_all("pyramid-level-new"):
        key = (lvl.get("notes") or "").lower()
        if key in sections:
            sections[key] = _notes_from_anchors(lvl)

    if not any(sections.values()):
        pyramid = soup.find(id="pyramid") or soup
        flat = _notes_from_anchors(pyramid)
        if flat:
            sections["top"] = flat
    return sections["top"], sections["middle"], sections["base"]


def _parse_accords(soup) -> list[str]:
    """
    Main accords are bars: a div with inline `background:` + `width:%` styling
    wrapping <span class="truncate">accord name</span>. The width is strength.
    """
    accords = []
    for span in soup.select("span.truncate"):
        parent = span.parent
        style = (parent.get("style") or "") if parent else ""
        if "width" in style and "background" in style:
            t = span.get_text(strip=True)
            if t:
                accords.append(t)
    return list(dict.fromkeys(accords))


def _parse_performance(soup) -> tuple[str | None, str | None]:
    """
    Aggregate longevity/sillage are no longer in the static HTML (rendered via JS
    from vote data); only per-user vote stubs remain. Return None and let
    season/occasion inference from accords carry the vibe signal.
    """
    return None, None


def _parse_perfume(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    rec = {"source": "fragrantica", "url": url}

    # JSON-LD first.
    ld = soup.find("script", type="application/ld+json")
    if ld and ld.string:
        try:
            data = json.loads(ld.string)
            if isinstance(data, list):
                data = data[0]
            brand = data.get("brand")
            rec["brand"] = brand.get("name") if isinstance(brand, dict) else brand
            rec["name"] = _clean_name(data.get("name"), rec.get("brand"))
            agg = data.get("aggregateRating") or {}
            rec["rating"] = _to_float(agg.get("ratingValue"))
            rec["rating_count"] = _to_int(agg.get("ratingCount"))
            rec["image_url"] = data.get("image")
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass

    # itemprop fallbacks.
    if not rec.get("brand"):
        rec["brand"] = _text(soup.find("span", itemprop="name")) or _text(soup.find("a", class_="brand"))
    if not rec.get("name"):
        h1 = soup.find("h1", itemprop="name") or soup.find("h1")
        rec["name"] = _clean_name(_text(h1), rec.get("brand"))
    if rec.get("rating") is None:
        rec["rating"] = _to_float(_text(soup.find("span", itemprop="ratingValue")))
    if rec.get("rating_count") is None:
        rec["rating_count"] = _to_int(_text(soup.find("span", itemprop="ratingCount")))

    desc_el = soup.find("div", itemprop="description")
    desc = _text(desc_el)
    if desc:
        rec["description"] = desc
        ym = LAUNCH_YEAR.search(desc)
        if ym:
            rec["year"] = int(ym.group(1))

    # Gender from h1 text.
    h1text = _text(soup.find("h1")) or ""
    low = h1text.lower()
    if "for women and men" in low:
        rec["gender"] = "unisex"
    elif "for women" in low:
        rec["gender"] = "women"
    elif "for men" in low:
        rec["gender"] = "men"

    rec["top_notes"], rec["middle_notes"], rec["base_notes"] = _parse_notes(soup)
    accords = _parse_accords(soup)
    rec["accords"] = json.dumps(accords) if accords else None
    rec["season"] = infer_season(accords) or None
    rec["occasion"] = infer_occasion(accords) or None
    rec["longevity"], rec["sillage"] = _parse_performance(soup)

    return {k: v for k, v in rec.items() if v is not None}


def _to_float(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Batch scrape (the workhorse)
# --------------------------------------------------------------------------- #

def _has_required(rec: dict) -> bool:
    """Core fields a usable record must have (drives the Stage-2 decision)."""
    return bool(rec.get("name") and rec.get("brand")
                and (rec.get("top_notes") or rec.get("accords")))


async def scrape_batch(batch_size: int = 100) -> int:
    """Fetch + parse + upsert a bounded batch of pending URLs, then sync to Qdrant.

    Two-stage: curl_cffi first; if required fields are missing, fall back to
    Playwright (when available) and merge what it recovers."""
    if not net.is_online():
        return 0  # offline — leave the queue untouched (no burned retries)
    targets = db.get_pending_targets(batch_size)
    if not targets:
        return 0

    scraped = 0
    for t in targets:
        url = t["url"]
        html = await asyncio.to_thread(_fetch, url)
        if not html:
            # curl_cffi blocked (403 / Cloudflare). Try Stage 2 before giving up —
            # only if crawl-Playwright is enabled (headed windows are opt-in).
            if settings.ENABLE_CRAWL_PLAYWRIGHT and playwright_fetch.available() and net.is_online():
                html = await playwright_fetch.render_html(url)
            if not html:
                db.mark_target_failed(url, "fetch failed")
                await asyncio.sleep(random.uniform(settings.SCRAPE_BACKOFF_MIN, settings.SCRAPE_BACKOFF_MAX))  # backoff
                continue
        try:
            rec = _parse_perfume(html, url)
            # Stage 2: render with Playwright only when Stage 1 came up short.
            if not _has_required(rec) and settings.ENABLE_CRAWL_PLAYWRIGHT \
                    and playwright_fetch.available():
                html2 = await playwright_fetch.render_html(url)
                if html2:
                    for key, val in _parse_perfume(html2, url).items():
                        if val and not rec.get(key):
                            rec[key] = val
            if not rec.get("name") or not rec.get("brand"):
                db.mark_target_failed(url, "no name/brand parsed")
            else:
                if t.get("is_new"):
                    rec["new_release"] = 1
                db.upsert_perfume(rec)
                db.mark_target_done(url)
                scraped += 1
        except Exception as e:
            db.mark_target_failed(url, str(e))
        await asyncio.sleep(random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX))  # politeness delay

    if scraped:
        await qdrant_store.sync_unsynced()
        await asyncio.to_thread(db.rebuild_fts)  # keep sparse index current
    log.info("scrape_batch: scraped %d / %d targets", scraped, len(targets))
    return scraped


# --------------------------------------------------------------------------- #
# Continuous crawl (drains the whole queue, politely, in the background)
# --------------------------------------------------------------------------- #

_crawl_active = False


def crawl_active() -> bool:
    return _crawl_active


def stop_crawl() -> None:
    global _crawl_active
    _crawl_active = False
    log.info("continuous crawl: stop requested")


async def continuous_scrape(batch_size: int = 40) -> None:
    """Run scrape batches back-to-back until the queue drains or stop is called.

    Politeness delays live inside scrape_batch, so this just keeps feeding it.
    Safe to call once; a second call while active is a no-op.
    """
    global _crawl_active
    if _crawl_active:
        return
    _crawl_active = True
    log.info("continuous crawl: started")
    try:
        idle = 0
        while _crawl_active:
            if not net.is_online():
                await asyncio.sleep(60)        # paused while offline
                continue
            n = await scrape_batch(batch_size)
            if n == 0 and not db.get_pending_targets(1):
                idle += 1
                if idle >= 2:
                    break  # queue genuinely empty
                await asyncio.sleep(30)
            else:
                idle = 0
    finally:
        _crawl_active = False
        log.info("continuous crawl: stopped")


async def full_crawl() -> None:
    """
    Discover the whole catalog and scrape it CONCURRENTLY: the scraper drains the
    queue while discovery keeps feeding it, so perfumes start landing immediately
    instead of waiting hours for discovery to finish.
    """
    asyncio.create_task(continuous_scrape())
    await asyncio.sleep(1)  # let the scraper register as active
    await discover_catalog()
    # continuous_scrape keeps running until the queue drains.


# --------------------------------------------------------------------------- #
# Playwright enrichment — the JS-rendered "reminds me of" box + vote charts
# --------------------------------------------------------------------------- #

# Ordered buckets per metric, exactly as rendered ("no vote" kept for tokenizing
# context but excluded from output).
_VOTE_METRICS = {
    "longevity": ["no vote", "very weak", "weak", "moderate", "long lasting", "eternal"],
    "sillage": ["no vote", "intimate", "moderate", "strong", "enormous"],
}


def _parse_count(s: str) -> int | None:
    """Parse a vote count, handling k/m suffixes ('6.6k' → 6600)."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([km]?)", s.strip().lower().replace(",", ""))
    if not m:
        return None
    v = float(m.group(1))
    return int(v * {"k": 1000, "m": 1_000_000}.get(m.group(2), 1))


def _parse_box(soup, exclude_fid: str | None = None) -> list[dict]:
    """Box entries (rank-ordered) from the rendered #similar component."""
    container = soup.select_one("#similar") or soup
    out, seen = [], set()
    for a in container.select("a[href*='/perfume/']"):
        href = a.get("href", "")
        fid = db.frag_id(href)
        if not fid or fid == exclude_fid or fid in seen:
            continue
        seen.add(fid)
        name = a.get_text(strip=True)
        if not name:
            img = a.find("img")
            name = img.get("alt") if img else None
        out.append({"frag_id": fid, "url": _abs(href), "name": name})
    return out


def _parse_votes(soup) -> dict:
    """Vote distributions from the rendered page (Gap 4).

    The chart renders as 'LONGEVITY | no vote | very weak | 525 | weak | 927 | …'.
    We locate each metric's container, tokenize, and read the count token right
    after each EXACT bucket token (so 'weak' isn't confused with 'very weak').
    Returns {} if the charts aren't present (e.g. Stage-1 static HTML)."""
    result: dict[str, dict] = {}
    for metric, buckets in _VOTE_METRICS.items():
        last = buckets[-1]
        label = soup.find(string=re.compile(metric, re.I))
        if not label:
            continue
        container, node = None, label.parent
        for _ in range(6):
            if node is None:
                break
            t = node.get_text(" ", strip=True).lower()
            if last in t and metric in t:
                container = node
                break
            node = node.parent
        if container is None:
            continue
        tokens = [x.strip() for x in container.get_text("|", strip=True).split("|") if x.strip()]
        dist = {}
        for i, tok in enumerate(tokens[:-1]):
            tl = tok.lower()
            if tl in buckets and tl != "no vote":
                count = _parse_count(tokens[i + 1])
                if count is not None:
                    dist[tl] = count
        if dist:
            result[metric] = dist
    return result


async def enrich_perfume(url: str) -> dict:
    """Render a perfume page and harvest community evidence: the "reminds me of"
    box → high-confidence smells_like edges; vote charts → consensus performance."""
    if not playwright_fetch.available():
        return {"error": "playwright not available"}
    if not net.is_online():
        return {"error": "offline"}
    html = await playwright_fetch.render_html(url, wait_selector="#similar a[href*='/perfume/']")
    if not html:
        return {"error": "render failed"}

    soup = BeautifulSoup(html, "lxml")
    src_fid = db.frag_id(url)
    box = _parse_box(soup, exclude_fid=src_fid)
    votes = _parse_votes(soup)

    edges = 0
    if src_fid and box:
        import relationship_service
        edges = relationship_service.record_box_relationships(
            src_fid, box, rel_type="smells_like", source="fragrantica_box")
    if src_fid and votes:
        row = db.get_by_frag_id(src_fid)
        if row:
            db.set_votes(row["id"], votes.get("longevity"), votes.get("sillage"))

    log.info("enrich %s: box=%d edges=%d votes=%s", url, len(box), edges, bool(votes))
    return {"url": url, "box": len(box), "edges": edges, "votes": votes}
