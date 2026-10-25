"""Tips plugin module."""

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}/tips/groupList")
@bind(GL_V1)
async def _handle_group_list(_: Request) -> dict[str, list[object]]:
    """Get tips group list."""
    return {"moduleList": []}


@routes.view(f"{BASE_URL}/tips/tipsList")
@bind(GL_V1)
async def _handle_tips_list(_: Request) -> dict[str, list[object]]:
    """Get tips list."""
    return {"tipsList": []}
