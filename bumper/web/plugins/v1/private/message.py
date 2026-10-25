"""Message plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}message/hasUnreadMsg")
@bind(GL_V1)
async def _handle_has_unread_message(_: Request) -> Any:
    """Has unread message."""
    return "N"


@routes.view(f"{BASE_URL}message/getMsgList")
@bind(GL_V1)
async def _handle_get_msg_list(_: Request) -> Any:
    """Get msg list."""
    return {"hasNextPage": 0, "items": []}
