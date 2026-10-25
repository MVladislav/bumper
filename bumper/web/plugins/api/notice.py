"""Notice plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import LEGACY_BARE, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/notice/app")
@bind(LEGACY_BARE)
async def _handle_notice_app(_: Request) -> Any:
    return {}
