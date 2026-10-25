"""Member plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind
from bumper.web.plugins.v1.private.member import handle_get_exp_by_scene

from . import BASE_URL

routes = web.RouteTableDef()

routes.view(f"{BASE_URL}member/getExpByScene")(handle_get_exp_by_scene)


@routes.view(f"{BASE_URL}member/getBindBenefit")
@bind(GL_V1)
async def _handle_get_bind_benefit(_: Request) -> Any:
    """Get bind benefit."""
    return {"completeList": []}
