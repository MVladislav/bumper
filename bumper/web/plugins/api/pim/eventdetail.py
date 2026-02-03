"""Pim Event Detail plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_event_detail

_LOGGER = logging.getLogger(__name__)


class EventDetailPlugin(WebserverPlugin):
    """Event Detail plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/eventdetail.html", _handle_event_detail),
        ]


async def _handle_event_detail(_: Request) -> Response:
    """Handle Event Detail."""
    return web.Response(text=get_event_detail(), content_type="text/html")
