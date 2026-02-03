"""Offline plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_offline

_LOGGER = logging.getLogger(__name__)


class OfflinePlugin(WebserverPlugin):
    """Offline plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/offline.html", _handle_offline),
        ]


async def _handle_offline(_: Request) -> Response:
    """Handle Offline."""
    return web.Response(text=get_offline(), content_type="text/html")
