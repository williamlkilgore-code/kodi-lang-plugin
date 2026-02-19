"""HTTP client wrapper using urllib. Centralizes timeouts, retries, headers, and per-domain throttle."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from lib.core.log import log_debug, log_error

ADDON_ID = "plugin.video.langscrape"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Per-domain timestamps for throttle
_last_request: dict[str, float] = {}
_THROTTLE_MS = 350  # min ms between calls to the same domain


def _get_settings() -> tuple[int, int, str]:
    """Return (timeout_sec, retries, user_agent) from addon settings."""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon(ADDON_ID)
        timeout = int(addon.getSetting("timeout") or "12")
        retries = int(addon.getSetting("retries") or "2")
        ua = addon.getSetting("useragent_override") or ""
    except Exception:
        timeout, retries, ua = 12, 2, ""
    return timeout, retries, ua or DEFAULT_UA


def _throttle(domain: str) -> None:
    now = time.monotonic()
    last = _last_request.get(domain, 0.0)
    wait = (_THROTTLE_MS / 1000.0) - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[domain] = time.monotonic()


def fetch(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int | None = None,
    retries: int | None = None,
) -> tuple[str, int]:
    """Fetch a URL and return (body_text, status_code). Retries on transient errors."""
    settings_timeout, settings_retries, ua = _get_settings()
    timeout = timeout or settings_timeout
    retries = retries if retries is not None else settings_retries

    req_headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "fa,en;q=0.9",
    }
    if headers:
        req_headers.update(headers)

    from urllib.parse import urlparse as _urlparse
    domain = _urlparse(url).netloc
    _throttle(domain)

    log_debug("HTTP GET %s", url)

    last_error = None
    for attempt in range(1 + retries):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
                log_debug("HTTP %d (%d bytes)", status, len(body))
                return body, status
        except urllib.error.HTTPError as exc:
            log_error("HTTP error %d on %s (attempt %d)", exc.code, url, attempt + 1)
            last_error = exc
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(1 * (attempt + 1))
                continue
            return "", exc.code
        except Exception as exc:
            log_error("Request failed: %s (attempt %d)", exc, attempt + 1)
            last_error = exc
            if attempt < retries:
                time.sleep(1 * (attempt + 1))

    log_error("All retries exhausted for %s: %s", url, last_error)
    return "", 0


def fetch_json(url: str, headers: dict[str, str] | None = None) -> tuple[Any, int]:
    """Fetch a URL and parse the response as JSON."""
    body, status = fetch(url, headers=headers)
    if not body:
        return None, status
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            log_debug("JSON top-level keys: %s", list(data.keys()))
        return data, status
    except json.JSONDecodeError as exc:
        log_error("JSON parse error for %s: %s", url, exc)
        return None, status
