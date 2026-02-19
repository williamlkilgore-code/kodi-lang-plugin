"""Merge and de-duplicate video results from multiple providers."""
from __future__ import annotations

from lib.core.models import ProviderResult, VideoItem


def _dedup_key(item: VideoItem) -> str:
    """Build a key for dedup: normalized title + duration + provider."""
    title = item.title.strip().lower()
    dur = item.duration or 0
    return "%s|%d|%s" % (title, dur, item.provider_id)


def merge_results(results: list[ProviderResult]) -> ProviderResult:
    """Merge multiple ProviderResults, removing duplicates by title+duration+provider."""
    seen: set[str] = set()
    merged_items: list[VideoItem] = []

    for pr in results:
        for item in pr.items:
            key = _dedup_key(item)
            if key not in seen:
                seen.add(key)
                merged_items.append(item)

    # Sort by published date descending (newest first), None dates at end
    merged_items.sort(
        key=lambda v: v.published.timestamp() if v.published else 0,
        reverse=True,
    )

    return ProviderResult(items=merged_items)
