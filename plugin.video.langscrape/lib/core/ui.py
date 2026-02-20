"""Kodi UI helpers: list items, dialogs, keyboard input, playback."""
from __future__ import annotations

from lib.core.log import log_debug, log_error, log_info
from lib.core.models import ProviderResult, StreamInfo

try:
    import xbmc
    import xbmcgui
    import xbmcplugin

    _IN_KODI = True
except ImportError:
    _IN_KODI = False


def get_search_query() -> str | None:
    """Show Kodi on-screen keyboard and return the typed text, or None if cancelled."""
    if not _IN_KODI:
        return None
    kb = xbmc.Keyboard("", "Search")  # noqa: F821
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText().strip() or None
    return None


def show_home(router):
    """Display the top-level language/provider menu."""
    if not _IN_KODI:
        return

    items = []

    # Aparat (Farsi)
    li = xbmcgui.ListItem("Aparat (Farsi)")
    url = router.build_url(action="aparat.menu")
    items.append((url, li, True))

    xbmcplugin.addDirectoryItems(router.handle, items, len(items))
    xbmcplugin.endOfDirectory(router.handle)


def show_provider_menu(router, provider_id: str):
    """Show Search / Recent menu for a provider."""
    if not _IN_KODI:
        return

    items = []

    li_search = xbmcgui.ListItem("Search")
    url_search = router.build_url(action="%s.search" % provider_id)
    items.append((url_search, li_search, True))

    li_recent = xbmcgui.ListItem("Recent Videos")
    url_recent = router.build_url(action="%s.recent" % provider_id)
    items.append((url_recent, li_recent, True))

    xbmcplugin.addDirectoryItems(router.handle, items, len(items))
    xbmcplugin.endOfDirectory(router.handle)


def show_video_list(router, result: ProviderResult, provider_id: str, query: str | None = None):
    """Render a list of VideoItems as playable Kodi list items."""
    if not _IN_KODI:
        return

    if not result.items:
        xbmcgui.Dialog().notification("LangScrape", "No results found", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(router.handle, succeeded=False)
        return

    items = []
    for video in result.items:
        li = xbmcgui.ListItem(video.title)
        li.setProperty("IsPlayable", "true")

        info_tag = li.getVideoInfoTag()
        if video.title:
            info_tag.setTitle(video.title)
        if video.plot:
            info_tag.setPlot(video.plot)
        if video.duration:
            info_tag.setDuration(video.duration)

        if video.thumb:
            li.setArt({"thumb": video.thumb, "icon": video.thumb})

        url = router.build_url(
            action="%s.play" % provider_id,
            videohash=video.videohash or "",
        )
        items.append((url, li, False))

    xbmcplugin.addDirectoryItems(router.handle, items, len(items))

    # Next page link
    if result.next_page_token:
        li_next = xbmcgui.ListItem("Next Page >>")
        params = {"action": "%s.recent" % provider_id, "page": result.next_page_token}
        if query:
            params["action"] = "%s.search" % provider_id
            params["query"] = query
        from urllib.parse import urlencode
        url_next = "%s?%s" % (router.base_url, urlencode(params))
        xbmcplugin.addDirectoryItem(router.handle, url_next, li_next, True)

    xbmcplugin.setContent(router.handle, "videos")
    xbmcplugin.endOfDirectory(router.handle)


def play_stream(router, stream_info: StreamInfo | None):
    """Resolve and play a stream via setResolvedUrl."""
    if not _IN_KODI:
        return

    if not stream_info or not stream_info.selected:
        log_error("No playable stream found")
        xbmcgui.Dialog().notification(
            "LangScrape", "No playable stream found", xbmcgui.NOTIFICATION_ERROR
        )
        xbmcplugin.setResolvedUrl(router.handle, False, xbmcgui.ListItem())
        return

    candidate = stream_info.selected
    log_info(
        "Playing %s stream at %sq: %s",
        candidate.kind,
        candidate.quality or "auto",
        candidate.url[:120],
    )

    li = xbmcgui.ListItem(path=candidate.url)

    # Attach headers if needed
    if candidate.headers:
        header_str = "&".join("%s=%s" % (k, v) for k, v in candidate.headers.items())
        li.setProperty("inputstream.adaptive.stream_headers", header_str)
        li.setPath(candidate.url + "|" + header_str)

    # If HLS, hint the input stream
    if candidate.kind == "hls":
        li.setMimeType("application/vnd.apple.mpegurl")
        li.setContentLookup(False)

    xbmcplugin.setResolvedUrl(router.handle, True, li)
