"""Ad plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL


class AdPlugin(WebserverPlugin):
    """Ad plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}ad/getAdByPositionType", _handle),
            web.route("*", f"{BASE_URL}ad/getBootScreen", _handle),
        ]


async def _handle(_: Request) -> Response:
    return response_success_v1(None)
