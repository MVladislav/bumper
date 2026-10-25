"""Pim plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.utils import utils
from bumper.web.static_api import get_offline

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/pim/offline.html")
async def _handle_offline(_: Request) -> Response:
    """Handle offline."""
    return web.Response(text=get_offline(), content_type="text/html")


@routes.view(f"{PREFIX}/pim/network_setup_preparation_by_series.html")
async def _handle_network_setup_preparation_by_series(_: Request) -> Response:
    """Handle network setup preparation by series."""
    utils.default_log_warn_not_impl("_handle_network_setup_preparation_by_series")
    return web.Response(text="🤖", content_type="text/html")


@routes.view(f"{PREFIX}/pim/find_qrcode.html")
async def _handle_find_qrcode(_: Request) -> Response:
    """Handle find qrcode."""
    utils.default_log_warn_not_impl("_handle_find_qrcode")
    return web.Response(text="🤖", content_type="text/html")


@routes.view(f"{PREFIX}/pim/faq_problem_new.html")
async def _handle_faq_problem_new(_: Request) -> Response:
    """Handle faq problem new."""
    utils.default_log_warn_not_impl("_handle_faq_problem_new")
    return web.Response(text="🤖", content_type="text/html")


@routes.view(f"{PREFIX}/pim/active_discovery.html")
async def _handle_active_discovery(_: Request) -> Response:
    """Handle active discovery."""
    utils.default_log_warn_not_impl("_handle_active_discovery")
    return web.Response(text="🤖", content_type="text/html")


@routes.view(f"{PREFIX}/pim/viewWiFi.html")
async def _handle_view_wifi(_: Request) -> Response:
    """Handle view WiFi."""
    utils.default_log_warn_not_impl("_handle_view_wifi")
    return web.Response(text="🤖", content_type="text/html")
