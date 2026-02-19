"""Tests for Aparat provider parsing logic using JSON fixtures."""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

from lib.providers.aparat import (
    _parse_video_item,
    _parse_duration,
    _parse_date,
    _extract_stream_candidates,
    _detect_stream_kind,
    _extract_quality_from_profile,
    _extract_quality_from_url,
    _select_best_stream,
)
from lib.core.models import StreamCandidate


# --- Duration parsing ---

def test_parse_duration_int():
    assert _parse_duration(754) == 754


def test_parse_duration_float():
    assert _parse_duration(12.5) == 12


def test_parse_duration_mmss():
    assert _parse_duration("12:34") == 754


def test_parse_duration_hhmmss():
    assert _parse_duration("1:02:03") == 3723


def test_parse_duration_empty():
    assert _parse_duration("") is None
    assert _parse_duration(None) is None


# --- Date parsing ---

def test_parse_date_slash_full():
    dt = _parse_date("2024/06/15 14:30:00")
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 6
    assert dt.day == 15


def test_parse_date_slash_short():
    dt = _parse_date("2024/06/10")
    assert dt is not None
    assert dt.year == 2024


def test_parse_date_invalid():
    assert _parse_date("not a date") is None


# --- Video item parsing from fixture ---

def test_parse_search_fixture():
    with open(os.path.join(FIXTURES, "aparat_search.json")) as f:
        data = json.load(f)

    raw_list = data["videobysearch"]
    items = [_parse_video_item(v) for v in raw_list]

    # First item: full data
    assert items[0] is not None
    assert items[0].title == "آموزش پایتون - درس اول"
    assert items[0].videohash == "Abc12"
    assert items[0].duration == 754  # "12:34"
    assert items[0].published is not None
    assert items[0].provider_id == "aparat"
    assert items[0].language == "fa"
    assert "big" in items[0].thumb

    # Second item: integer duration
    assert items[1] is not None
    assert items[1].duration == 3600

    # Third item: empty uid means title-only, still valid since title exists
    assert items[2] is not None
    assert items[2].title == "تست بدون uid"


# --- Stream candidate extraction ---

def test_extract_candidates_from_fixture():
    with open(os.path.join(FIXTURES, "aparat_video.json")) as f:
        data = json.load(f)

    candidates = _extract_stream_candidates(data["video"])
    assert len(candidates) >= 4  # 4 from file_link_all + 1 from file_link (may dedup)

    qualities = [c.quality for c in candidates if c.quality is not None]
    assert 1080 in qualities
    assert 720 in qualities
    assert 480 in qualities

    kinds = set(c.kind for c in candidates)
    assert "mp4" in kinds
    assert "hls" in kinds


# --- Stream kind detection ---

def test_detect_mp4():
    assert _detect_stream_kind("https://cdn.com/video.mp4") == "mp4"


def test_detect_hls():
    assert _detect_stream_kind("https://cdn.com/video.m3u8") == "hls"


def test_detect_dash():
    assert _detect_stream_kind("https://cdn.com/video.mpd") == "dash"


# --- Quality extraction ---

def test_quality_from_profile():
    assert _extract_quality_from_profile("720p") == 720
    assert _extract_quality_from_profile("h_1080_hls") == 1080
    assert _extract_quality_from_profile("unknown") is None


def test_quality_from_url():
    assert _extract_quality_from_url("https://cdn.com/Abc12-720p.mp4") == 720
    assert _extract_quality_from_url("https://cdn.com/v/480/file.mp4") == 480


# --- Stream selection ---

def test_select_highest_auto(monkeypatch):
    monkeypatch.setattr("lib.providers.aparat._preferred_quality", lambda: 0)
    monkeypatch.setattr("lib.providers.aparat._prefer_hls", lambda: False)

    candidates = [
        StreamCandidate(url="a", kind="mp4", quality=480),
        StreamCandidate(url="b", kind="mp4", quality=1080),
        StreamCandidate(url="c", kind="mp4", quality=720),
    ]
    selected = _select_best_stream(candidates)
    assert selected.quality == 1080


def test_select_exact_quality(monkeypatch):
    monkeypatch.setattr("lib.providers.aparat._preferred_quality", lambda: 720)
    monkeypatch.setattr("lib.providers.aparat._prefer_hls", lambda: False)

    candidates = [
        StreamCandidate(url="a", kind="mp4", quality=480),
        StreamCandidate(url="b", kind="mp4", quality=1080),
        StreamCandidate(url="c", kind="mp4", quality=720),
    ]
    selected = _select_best_stream(candidates)
    assert selected.quality == 720


def test_select_nearest_under(monkeypatch):
    monkeypatch.setattr("lib.providers.aparat._preferred_quality", lambda: 720)
    monkeypatch.setattr("lib.providers.aparat._prefer_hls", lambda: False)

    candidates = [
        StreamCandidate(url="a", kind="mp4", quality=480),
        StreamCandidate(url="b", kind="mp4", quality=1080),
    ]
    selected = _select_best_stream(candidates)
    assert selected.quality == 480


def test_prefer_hls(monkeypatch):
    monkeypatch.setattr("lib.providers.aparat._preferred_quality", lambda: 0)
    monkeypatch.setattr("lib.providers.aparat._prefer_hls", lambda: True)

    candidates = [
        StreamCandidate(url="a", kind="mp4", quality=1080),
        StreamCandidate(url="b", kind="hls", quality=720),
    ]
    selected = _select_best_stream(candidates)
    assert selected.kind == "hls"
    assert selected.quality == 720
