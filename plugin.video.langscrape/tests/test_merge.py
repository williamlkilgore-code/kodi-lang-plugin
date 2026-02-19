"""Tests for merge/dedupe logic."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from lib.core.models import ProviderResult, VideoItem
from lib.core.merge import merge_results


def _make_item(title, duration=None, provider="aparat", published=None):
    return VideoItem(
        title=title,
        url="http://example.com/v/test",
        duration=duration,
        provider_id=provider,
        published=published,
    )


def test_merge_empty():
    result = merge_results([])
    assert result.items == []


def test_merge_single():
    pr = ProviderResult(items=[_make_item("Video A")])
    result = merge_results([pr])
    assert len(result.items) == 1
    assert result.items[0].title == "Video A"


def test_dedup_same_title_duration_provider():
    pr1 = ProviderResult(items=[_make_item("Video A", 120, "aparat")])
    pr2 = ProviderResult(items=[_make_item("Video A", 120, "aparat")])
    result = merge_results([pr1, pr2])
    assert len(result.items) == 1


def test_no_dedup_different_provider():
    pr1 = ProviderResult(items=[_make_item("Video A", 120, "aparat")])
    pr2 = ProviderResult(items=[_make_item("Video A", 120, "other")])
    result = merge_results([pr1, pr2])
    assert len(result.items) == 2


def test_sort_by_date():
    items = [
        _make_item("Old", published=datetime(2020, 1, 1)),
        _make_item("New", published=datetime(2024, 6, 1)),
        _make_item("Mid", published=datetime(2022, 6, 1)),
    ]
    pr = ProviderResult(items=items)
    result = merge_results([pr])
    assert result.items[0].title == "New"
    assert result.items[1].title == "Mid"
    assert result.items[2].title == "Old"


def test_none_dates_sort_last():
    items = [
        _make_item("No Date"),
        _make_item("Has Date", published=datetime(2024, 1, 1)),
    ]
    pr = ProviderResult(items=items)
    result = merge_results([pr])
    assert result.items[0].title == "Has Date"
    assert result.items[1].title == "No Date"
