"""Message plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL


class MessagePlugin(WebserverPlugin):
    """Message plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}message/hasUnreadMsg", _handle_has_unread_message),
            web.route("*", f"{BASE_URL}message/getMsgList", _handle_get_msg_list),
        ]


async def _handle_has_unread_message(_: Request) -> Response:
    """Has unread message."""
    return response_success_v1("N")


async def _handle_get_msg_list(_: Request) -> Response:
    """Get msg list."""
    return response_success_v1({"hasNextPage": 0, "items": []})
