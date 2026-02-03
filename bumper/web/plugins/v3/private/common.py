"""Common plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.v2.private.common import handle_get_bottom_navigate_info_list

from . import BASE_URL


class CommonPlugin(WebserverPlugin):
    """Common plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}common/getBottomNavigateInfoList", handle_get_bottom_navigate_info_list),
        ]
