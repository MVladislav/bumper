"""Notice plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v4

_LOGGER = logging.getLogger(__name__)


class NoticePlugin(WebserverPlugin):
    """Notice plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/notice/app", _handle_notice_app),
        ]


async def _handle_notice_app(_: Request) -> Response:
    return response_success_v4(data={})
