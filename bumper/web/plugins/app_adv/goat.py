"""Goat guide plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.goat import goat_page

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/goat/winter_guide.html")
async def _handle_winter_guide(_: Request) -> Response:
    """Winter guide."""
    return goat_page("winter_guide")


@routes.view(f"{PREFIX}/goat/maintenance_guide_o_series.html")
async def _handle_maintenance_guide(_: Request) -> Response:
    """Maintenance guide of the O series."""
    return goat_page("maintenance_guide_o_series")


@routes.view(f"{PREFIX}/goat/pin_code_settings.html")
async def _handle_pin_code_settings(_: Request) -> Response:
    """PIN code settings."""
    return goat_page("pin_code_settings")


@routes.view(f"{PREFIX}/goat/rtk.html")
async def _handle_rtk(_: Request) -> Response:
    """RTK installation guide."""
    return goat_page("rtk_install_method")
