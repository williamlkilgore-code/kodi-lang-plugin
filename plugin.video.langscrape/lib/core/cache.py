"""TTL-based disk cache using xbmcvfs (or filesystem fallback for testing)."""
from __future__ import annotations

import hashlib
import json
import os
import time

from lib.core.log import log_debug

ADDON_ID = "plugin.video.langscrape"


def _cache_dir() -> str:
    try:
        import xbmcvfs
        path = xbmcvfs.translatePath(
            "special://profile/addon_data/%s/cache/" % ADDON_ID
        )
    except ImportError:
        path = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
    os.makedirs(path, exist_ok=True)
    return path


def _cache_enabled() -> bool:
    try:
        import xbmcaddon
        return xbmcaddon.Addon(ADDON_ID).getSettingBool("cache_enabled")
    except Exception:
        return True


def _make_key(url: str, extra: str = "") -> str:
    raw = url + extra
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get(url: str, ttl_seconds: int, extra: str = "") -> str | None:
    """Return cached body text if still valid, else None."""
    if not _cache_enabled():
        return None

    key = _make_key(url, extra)
    filepath = os.path.join(_cache_dir(), key + ".json")

    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            entry = json.load(f)
        if time.time() - entry.get("ts", 0) > ttl_seconds:
            log_debug("Cache expired for key=%s", key)
            return None
        log_debug("Cache hit for key=%s", key)
        return entry.get("body", "")
    except Exception:
        return None


def put(url: str, body: str, extra: str = "") -> None:
    """Store body text in cache."""
    if not _cache_enabled():
        return

    key = _make_key(url, extra)
    filepath = os.path.join(_cache_dir(), key + ".json")

    try:
        entry = {"ts": time.time(), "body": body}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f)
        log_debug("Cache put for key=%s", key)
    except Exception:
        pass


def clear_all() -> None:
    """Remove all cache files."""
    cache_dir = _cache_dir()
    for name in os.listdir(cache_dir):
        if name.endswith(".json"):
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass
