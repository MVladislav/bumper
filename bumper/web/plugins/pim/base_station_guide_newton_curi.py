"""Base station guide newton curi plugin module."""

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.static_api import get_base_station_guide_newton_curi, get_bot_image_path

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/base_station_guide_newton_curi.html")
async def _handle_base_station_guide_newton_curi(_: Request) -> Response:
    """Handle Base station guide newton curi."""
    return web.Response(text=get_base_station_guide_newton_curi(), content_type="text/html")


@routes.view(f"{PREFIX}/images/{{id}}")
async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())
