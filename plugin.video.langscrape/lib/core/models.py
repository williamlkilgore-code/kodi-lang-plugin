"""Data models for normalized video items and stream candidates."""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Literal


@dataclasses.dataclass
class VideoItem:
    title: str
    url: str
    videohash: str | None = None
    thumb: str | None = None
    plot: str | None = None
    published: datetime | None = None
    duration: int | None = None  # seconds
    provider_id: str = ""
    language: str = ""


@dataclasses.dataclass
class StreamCandidate:
    url: str
    kind: Literal["hls", "mp4", "dash"] = "mp4"
    quality: int | None = None  # e.g. 1080, 720
    headers: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class StreamInfo:
    selected: StreamCandidate | None = None
    alternates: list[StreamCandidate] = dataclasses.field(default_factory=list)
    is_drm: bool = False


@dataclasses.dataclass
class ProviderResult:
    items: list[VideoItem] = dataclasses.field(default_factory=list)
    next_page_token: str | None = None
    diagnostics: dict = dataclasses.field(default_factory=dict)
