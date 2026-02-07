"""Dim plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1


class DimPlugin(WebserverPlugin):
    """Dim plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/content/agreement", _handle_content_agreement),
        ]


async def _handle_content_agreement(_: Request) -> Response:
    """Content agreement."""
    return response_success_v1(None)
