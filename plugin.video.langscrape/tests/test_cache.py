"""Tests for the disk cache module."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.core import cache


def test_put_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cache, "_cache_enabled", lambda: True)

    cache.put("http://example.com/test", '{"ok": true}')
    result = cache.get("http://example.com/test", ttl_seconds=60)
    assert result == '{"ok": true}'


def test_expired_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cache, "_cache_enabled", lambda: True)

    cache.put("http://example.com/old", '{"old": true}')
    # Manually expire by setting ts in the past
    import json
    key = cache._make_key("http://example.com/old")
    filepath = os.path.join(str(tmp_path), key + ".json")
    with open(filepath, "r") as f:
        entry = json.load(f)
    entry["ts"] = time.time() - 9999
    with open(filepath, "w") as f:
        json.dump(entry, f)

    result = cache.get("http://example.com/old", ttl_seconds=60)
    assert result is None


def test_cache_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cache, "_cache_enabled", lambda: False)

    cache.put("http://example.com/no", "data")
    result = cache.get("http://example.com/no", ttl_seconds=60)
    assert result is None


def test_clear_all(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cache, "_cache_enabled", lambda: True)

    cache.put("http://a.com/1", "a")
    cache.put("http://b.com/2", "b")
    cache.clear_all()
    assert cache.get("http://a.com/1", 60) is None
    assert cache.get("http://b.com/2", 60) is None
