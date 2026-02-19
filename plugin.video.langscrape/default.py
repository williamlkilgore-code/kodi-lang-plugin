"""
plugin.video.langscrape - Multi-language video search and playback for Kodi.
Entry point: parses plugin URL and dispatches to the appropriate action.
"""
import sys

from lib.core.router import Router
from lib.core.log import log_debug


def main():
    router = Router(sys.argv)
    action = router.params.get("action", "home")
    log_debug("Dispatching action=%s params=%s", action, router.params)

    if action == "home":
        from lib.core.ui import show_home
        show_home(router)

    elif action == "aparat.menu":
        from lib.core.ui import show_provider_menu
        show_provider_menu(router, "aparat")

    elif action == "aparat.recent":
        from lib.providers.aparat import recent
        from lib.core.ui import show_video_list
        page = router.params.get("page")
        result = recent(page_token=page)
        show_video_list(router, result, "aparat")

    elif action == "aparat.search":
        from lib.providers.aparat import search
        from lib.core.ui import show_video_list, get_search_query
        query = router.params.get("query")
        if not query:
            query = get_search_query()
        if query:
            page = router.params.get("page")
            result = search(query, page_token=page)
            show_video_list(router, result, "aparat", query=query)

    elif action == "aparat.play":
        from lib.providers.aparat import resolve
        from lib.core.ui import play_stream
        videohash = router.params.get("videohash", "")
        stream_info = resolve(videohash)
        play_stream(router, stream_info)

    else:
        from lib.core.ui import show_home
        show_home(router)


if __name__ == "__main__":
    main()
