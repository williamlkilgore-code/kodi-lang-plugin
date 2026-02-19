"""Consistent logging wrapper with debug toggle from addon settings."""
from __future__ import annotations

ADDON_ID = "plugin.video.langscrape"

try:
    import xbmc
    import xbmcaddon

    def _addon():
        return xbmcaddon.Addon(ADDON_ID)

    def _debug_enabled():
        try:
            return _addon().getSettingBool("debug_logging")
        except Exception:
            return False

    def log_info(msg: str, *args):
        text = msg % args if args else msg
        xbmc.log("[%s] %s" % (ADDON_ID, text), xbmc.LOGINFO)

    def log_error(msg: str, *args):
        text = msg % args if args else msg
        xbmc.log("[%s] ERROR: %s" % (ADDON_ID, text), xbmc.LOGERROR)

    def log_debug(msg: str, *args):
        if not _debug_enabled():
            return
        text = msg % args if args else msg
        xbmc.log("[%s] DEBUG: %s" % (ADDON_ID, text), xbmc.LOGDEBUG)

except ImportError:
    # Outside Kodi (testing)
    import logging
    _logger = logging.getLogger(ADDON_ID)

    def log_info(msg: str, *args):
        _logger.info(msg, *args)

    def log_error(msg: str, *args):
        _logger.error(msg, *args)

    def log_debug(msg: str, *args):
        _logger.debug(msg, *args)
