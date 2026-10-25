"""Dim plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.post(f"{PREFIX}/content/agreement")
@bind(GL_V1)
async def _handle_content_agreement(_: Request) -> Any:
    """Content agreement."""
    return None
