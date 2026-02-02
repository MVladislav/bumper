"""Base station guide newton curi plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.images import get_bot_image
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_base_station_guide_newton_curi

_LOGGER = logging.getLogger(__name__)


class EventDetailPlugin(WebserverPlugin):
    """Base station guide newton curi plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                "/base_station_guide_newton_curi.html",
                _handle_base_station_guide_newton_curi,
            ),
            web.route(
                "*",
                "/images/{id}",
                get_bot_image,
            ),
        ]


async def _handle_base_station_guide_newton_curi(_: Request) -> Response:
    """Handle Base station guide newton curi."""
    return web.Response(text=get_base_station_guide_newton_curi(), content_type="text/html")
