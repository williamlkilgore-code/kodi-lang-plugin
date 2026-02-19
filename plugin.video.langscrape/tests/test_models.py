"""Tests for data models."""
import sys
import os

# Add plugin root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from lib.core.models import VideoItem, StreamCandidate, StreamInfo, ProviderResult


def test_video_item_defaults():
    v = VideoItem(title="Test", url="http://example.com")
    assert v.title == "Test"
    assert v.videohash is None
    assert v.thumb is None
    assert v.duration is None
    assert v.provider_id == ""
    assert v.language == ""


def test_video_item_full():
    v = VideoItem(
        title="Full",
        url="http://example.com/v/123",
        videohash="123",
        thumb="http://example.com/thumb.jpg",
        plot="A plot",
        published=datetime(2024, 1, 1),
        duration=600,
        provider_id="aparat",
        language="fa",
    )
    assert v.videohash == "123"
    assert v.duration == 600
    assert v.published.year == 2024


def test_stream_candidate_defaults():
    s = StreamCandidate(url="http://example.com/stream.mp4")
    assert s.kind == "mp4"
    assert s.quality is None
    assert s.headers == {}


def test_stream_info_no_drm():
    si = StreamInfo(
        selected=StreamCandidate(url="http://a.com/v.mp4"),
        alternates=[],
    )
    assert si.is_drm is False
    assert si.selected.url == "http://a.com/v.mp4"


def test_provider_result_empty():
    pr = ProviderResult()
    assert pr.items == []
    assert pr.next_page_token is None
