"""Ad plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}ad/getAdByPositionType")
@routes.view(f"{BASE_URL}ad/getBootScreen")
@bind(GL_V1)
async def _handle(_: Request) -> Any:
    return None
