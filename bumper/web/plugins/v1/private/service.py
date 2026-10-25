"""Service plugin module."""

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}/service/activityList")
@bind(GL_V1)
async def _handle_activity_list(_: Request) -> dict[str, list[object]]:
    """Get service activity list."""
    return {"activityList": []}


@routes.view(f"{BASE_URL}/service/groupList")
@bind(GL_V1)
async def _handle_group_list(_: Request) -> dict[str, list[object]]:
    """Get service group list."""
    return {"groupList": []}


@routes.view(f"{BASE_URL}/service/proactiveMessages")
@bind(GL_V1)
async def _handle_proactive_messages(_: Request) -> dict[str, object]:
    """Get proactive service messages."""
    return {"msgList": [], "hasMore": "N"}
