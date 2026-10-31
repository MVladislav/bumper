"""Goat guide plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.goat import goat_page

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/set_pin_code_guide.html")
async def _handle_set_pin_code_guide(_: Request) -> Response:
    """Set PIN code guide."""
    return goat_page("set_pin_code_guide")


@routes.view(f"{PREFIX}/advanced_features.html")
async def _handle_advanced_features(_: Request) -> Response:
    """Bluetooth advanced features guide."""
    return goat_page("advanced_features")
