"""Pim Event Detail plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.static_api import get_event_detail

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/eventdetail.html")
async def _handle_event_detail(_: Request) -> Response:
    """Handle Event Detail."""
    return web.Response(text=get_event_detail(), content_type="text/html")
