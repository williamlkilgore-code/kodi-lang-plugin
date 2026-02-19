"""Tests for the URL router."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.core.router import Router


def test_parse_empty_argv():
    r = Router([])
    assert r.base_url == ""
    assert r.handle == -1
    assert r.params == {}


def test_parse_home():
    r = Router(["plugin://plugin.video.langscrape/", "1", "?action=home"])
    assert r.base_url == "plugin://plugin.video.langscrape/"
    assert r.handle == 1
    assert r.params["action"] == "home"


def test_parse_search_with_query():
    r = Router([
        "plugin://plugin.video.langscrape/",
        "2",
        "?action=aparat.search&query=python&page=3",
    ])
    assert r.params["action"] == "aparat.search"
    assert r.params["query"] == "python"
    assert r.params["page"] == "3"


def test_build_url():
    r = Router(["plugin://plugin.video.langscrape/", "1", ""])
    url = r.build_url(action="aparat.play", videohash="Abc12")
    assert "action=aparat.play" in url
    assert "videohash=Abc12" in url
