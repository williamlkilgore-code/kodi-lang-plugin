"""
Aparat provider - search, recent, and stream resolution for aparat.com.

API endpoints (public, undocumented REST):
  - Video info:   GET https://www.aparat.com/etc/api/video/videohash/{HASH}
  - Search:       GET https://www.aparat.com/etc/api/videoBySearch/text/{Q}/perpage/{N}
  - Category:     GET https://www.aparat.com/etc/api/categoryVideos/cat/{ID}/perpage/{N}
  - By tag:       GET https://www.aparat.com/etc/api/videobytag/text/{TAG}
  - Recommend:    GET https://www.aparat.com/etc/api/videoRecom/videohash/{HASH}/perpage/{N}

Video info response shape (key: "video"):
  id, title, username, userid, visit_cnt, uid (videohash),
  big_poster, small_poster, duration, sdate, description,
  file_link, file_link_all (list of quality streams)
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

from lib.core import cache
from lib.core.http import fetch, fetch_json
from lib.core.log import log_debug, log_error, log_info
from lib.core.models import (
    ProviderResult,
    StreamCandidate,
    StreamInfo,
    VideoItem,
)

PROVIDER_ID = "aparat"
LANGUAGE = "fa"
BASE_URL = "https://www.aparat.com"
API_BASE = BASE_URL + "/etc/api"
PER_PAGE = 20

ADDON_ID = "plugin.video.langscrape"


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _preferred_quality() -> int:
    """Return preferred quality (0=Auto, or 1080/720/480)."""
    try:
        import xbmcaddon
        val = xbmcaddon.Addon(ADDON_ID).getSetting("preferred_quality") or "0"
        mapping = {"0": 0, "1": 1080, "2": 720, "3": 480}
        return mapping.get(val, 0)
    except Exception:
        return 0


def _prefer_hls() -> bool:
    try:
        import xbmcaddon
        return xbmcaddon.Addon(ADDON_ID).getSettingBool("prefer_hls")
    except Exception:
        return False


def _cache_ttl(kind: str) -> int:
    """Return TTL in seconds for a cache kind."""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon(ADDON_ID)
        if kind == "recent":
            return int(addon.getSetting("cache_ttl_recent") or "10") * 60
        elif kind == "search":
            return int(addon.getSetting("cache_ttl_search") or "20") * 60
        elif kind == "resolve":
            return int(addon.getSetting("cache_ttl_resolve") or "2") * 60
    except Exception:
        pass
    defaults = {"recent": 600, "search": 1200, "resolve": 120}
    return defaults.get(kind, 600)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_video_item(v: dict) -> VideoItem | None:
    """Convert a raw Aparat video dict to a VideoItem."""
    uid = v.get("uid") or v.get("videohash") or ""
    title = v.get("title", "")
    if not uid and not title:
        return None

    # Duration might be "12:34" string or int seconds
    duration = _parse_duration(v.get("duration"))

    # Published date
    published = None
    sdate = v.get("sdate") or v.get("sdate_timediff") or ""
    if sdate:
        published = _parse_date(sdate)

    thumb = v.get("big_poster") or v.get("small_poster") or v.get("preview_src") or ""

    return VideoItem(
        title=title,
        url="%s/v/%s" % (BASE_URL, uid) if uid else "",
        videohash=uid,
        thumb=thumb,
        plot=v.get("description") or v.get("cat_name") or "",
        published=published,
        duration=duration,
        provider_id=PROVIDER_ID,
        language=LANGUAGE,
    )


def _parse_duration(raw) -> int | None:
    """Parse duration: could be int seconds, float, or 'MM:SS' / 'HH:MM:SS' string."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    raw = str(raw).strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(float(raw))
    except (ValueError, TypeError):
        return None


def _parse_date(sdate: str) -> datetime | None:
    """Try to parse an Aparat date string."""
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(sdate.strip(), fmt)
        except ValueError:
            continue
    return None


def _fetch_api(endpoint: str, cache_kind: str = "recent") -> tuple[Any, int]:
    """Fetch an Aparat API endpoint with caching."""
    url = "%s/%s" % (API_BASE, endpoint)
    ttl = _cache_ttl(cache_kind)

    cached = cache.get(url, ttl)
    if cached:
        try:
            return json.loads(cached), 200
        except json.JSONDecodeError:
            pass

    data, status = fetch_json(url)
    if data and status == 200:
        cache.put(url, json.dumps(data))

    return data, status


# ---------------------------------------------------------------------------
# Provider contract: recent / search / resolve
# ---------------------------------------------------------------------------

def recent(page_token: str | None = None) -> ProviderResult:
    """Fetch recent/popular videos from Aparat."""
    endpoint = "categoryVideos/cat/1/perpage/%d" % PER_PAGE
    if page_token:
        endpoint += "/page/%s" % page_token

    data, status = _fetch_api(endpoint, "recent")
    if not data:
        log_error("Aparat recent: no data (status=%d)", status)
        return ProviderResult(diagnostics={"status": status, "error": "no_data"})

    raw_list = data.get("categoryvideos") or data.get("categoryVideos") or []
    items = []
    for v in raw_list:
        item = _parse_video_item(v)
        if item:
            items.append(item)

    log_debug("Aparat recent: parsed %d items", len(items))

    # Determine next page token — always offer next page if we got results
    next_page = None
    if items:
        current = int(page_token or "1")
        next_page = str(current + 1)

    return ProviderResult(
        items=items,
        next_page_token=next_page,
        diagnostics={"status": status, "count": len(items)},
    )


def search(query: str, page_token: str | None = None) -> ProviderResult:
    """Search Aparat for videos matching the query."""
    encoded_query = quote(query, safe="")
    endpoint = "videoBySearch/text/%s/perpage/%d" % (encoded_query, PER_PAGE)
    if page_token:
        endpoint += "/page/%s" % page_token

    data, status = _fetch_api(endpoint, "search")
    if not data:
        log_error("Aparat search: no data for q=%s (status=%d)", query, status)
        return ProviderResult(diagnostics={"status": status, "error": "no_data"})

    raw_list = data.get("videobysearch") or data.get("videoBySearch") or []
    items = []
    for v in raw_list:
        item = _parse_video_item(v)
        if item:
            items.append(item)

    log_debug("Aparat search q=%s: parsed %d items", query, len(items))

    # Always offer next page if we got results
    next_page = None
    if items:
        current = int(page_token or "1")
        next_page = str(current + 1)

    return ProviderResult(
        items=items,
        next_page_token=next_page,
        diagnostics={"status": status, "count": len(items), "query": query},
    )


def resolve(videohash: str) -> StreamInfo | None:
    """Resolve stream URLs for a given video hash."""
    if not videohash:
        log_error("Aparat resolve: empty videohash")
        return None

    endpoint = "video/videohash/%s" % videohash
    data, status = _fetch_api(endpoint, "resolve")
    if not data:
        log_error("Aparat resolve: no data for hash=%s (status=%d)", videohash, status)
        return None

    video_data = data.get("video")
    if not video_data:
        log_error("Aparat resolve: missing 'video' key for hash=%s", videohash)
        return None

    candidates = _extract_stream_candidates(video_data)
    log_debug("Aparat resolve hash=%s: %d stream candidates", videohash, len(candidates))

    if not candidates:
        log_error("Aparat resolve: no streams found for hash=%s", videohash)
        return None

    selected = _select_best_stream(candidates)
    remaining = [c for c in candidates if c is not selected]

    return StreamInfo(selected=selected, alternates=remaining)


def _extract_stream_candidates(video_data: dict) -> list[StreamCandidate]:
    """Extract stream candidates from Aparat video data."""
    candidates: list[StreamCandidate] = []
    headers = {"Referer": BASE_URL + "/"}

    # file_link_all: list of dicts with quality info and URLs
    file_link_all = video_data.get("file_link_all") or []
    if isinstance(file_link_all, list):
        for entry in file_link_all:
            if isinstance(entry, dict):
                urls = entry.get("urls") or []
                profile = entry.get("profile", "")
                quality = _extract_quality_from_profile(profile)

                for url in urls if isinstance(urls, list) else [urls] if urls else []:
                    if not url or not isinstance(url, str):
                        continue
                    kind = _detect_stream_kind(url)
                    candidates.append(StreamCandidate(
                        url=url, kind=kind, quality=quality, headers=headers,
                    ))
            elif isinstance(entry, str) and entry.startswith("http"):
                kind = _detect_stream_kind(entry)
                quality = _extract_quality_from_url(entry)
                candidates.append(StreamCandidate(
                    url=entry, kind=kind, quality=quality, headers=headers,
                ))

    # file_link: single direct URL
    file_link = video_data.get("file_link")
    if file_link and isinstance(file_link, str) and file_link.startswith("http"):
        kind = _detect_stream_kind(file_link)
        quality = _extract_quality_from_url(file_link)
        candidates.append(StreamCandidate(
            url=file_link, kind=kind, quality=quality, headers=headers,
        ))

    # file_link_all might also be a dict keyed by quality
    if isinstance(file_link_all, dict):
        for profile_key, url in file_link_all.items():
            if not url or not isinstance(url, str):
                continue
            quality = _extract_quality_from_profile(str(profile_key))
            kind = _detect_stream_kind(url)
            candidates.append(StreamCandidate(
                url=url, kind=kind, quality=quality, headers=headers,
            ))

    return candidates


def _detect_stream_kind(url: str) -> str:
    """Detect stream type from URL."""
    url_lower = url.lower()
    if ".m3u8" in url_lower or "hls" in url_lower:
        return "hls"
    elif ".mpd" in url_lower:
        return "dash"
    return "mp4"


def _extract_quality_from_profile(profile: str) -> int | None:
    """Extract quality integer from a profile string like '720p' or 'h_480'."""
    match = re.search(r"(\d{3,4})", profile)
    if match:
        return int(match.group(1))
    return None


def _extract_quality_from_url(url: str) -> int | None:
    """Try to extract quality from URL path segments."""
    match = re.search(r"[/_-](\d{3,4})p?[/_.\-]", url)
    if match:
        return int(match.group(1))
    return None


def _select_best_stream(candidates: list[StreamCandidate]) -> StreamCandidate:
    """Select the best stream based on user preferences."""
    preferred = _preferred_quality()
    hls_preferred = _prefer_hls()

    # Separate by kind
    hls_streams = [c for c in candidates if c.kind == "hls"]
    mp4_streams = [c for c in candidates if c.kind == "mp4"]

    # Pick pool based on preference
    pool = candidates
    if hls_preferred and hls_streams:
        pool = hls_streams
    elif mp4_streams:
        pool = mp4_streams

    if preferred == 0:
        # Auto: pick highest quality available
        with_q = [c for c in pool if c.quality is not None]
        if with_q:
            return max(with_q, key=lambda c: c.quality)
        return pool[0]

    # Exact match
    exact = [c for c in pool if c.quality == preferred]
    if exact:
        return exact[0]

    # Nearest quality not exceeding preferred
    under = [c for c in pool if c.quality is not None and c.quality <= preferred]
    if under:
        return max(under, key=lambda c: c.quality)

    # Fallback: lowest quality above preferred, or just first
    above = [c for c in pool if c.quality is not None and c.quality > preferred]
    if above:
        return min(above, key=lambda c: c.quality)

    return pool[0]
