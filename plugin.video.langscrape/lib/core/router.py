"""Parse Kodi plugin URL parameters into a dict and expose the addon handle."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse


class Router:
    def __init__(self, argv: list[str]):
        self.base_url: str = argv[0] if len(argv) > 0 else ""
        self.handle: int = int(argv[1]) if len(argv) > 1 else -1
        self.params: dict[str, str] = {}

        if len(argv) > 2:
            query = argv[2].lstrip("?")
            for key, values in parse_qs(query).items():
                self.params[key] = values[0]

    def build_url(self, **params: str) -> str:
        from urllib.parse import urlencode
        return "%s?%s" % (self.base_url, urlencode(params))
