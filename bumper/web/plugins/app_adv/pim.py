"""Pim plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_offline

_LOGGER = logging.getLogger(__name__)


class PimPlugin(WebserverPlugin):
    """Pim plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/pim/offline.html", _handle_offline),
            web.route("*", "/pim/network_setup_preparation_by_series.html", _handle_network_setup_preparation_by_series),
            web.route("*", "/pim/find_qrcode.html", _handle_find_qrcode),
            web.route("*", "/pim/faq_problem_new.html", _handle_faq_problem_new),
            web.route("*", "/pim/active_discovery.html", _handle_active_discovery),
            web.route("*", "/pim/viewWiFi.html", _handle_view_wifi),
        ]


async def _handle_offline(_: Request) -> Response:
    """Handle offline."""
    return web.Response(text=get_offline(), content_type="text/html")


async def _handle_network_setup_preparation_by_series(_: Request) -> Response:
    """Handle network setup preparation by series."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_network_setup_preparation_by_series")
    return web.Response(text="🤖", content_type="text/html")


async def _handle_find_qrcode(_: Request) -> Response:
    """Handle find qrcode."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_find_qrcode")
    return web.Response(text="🤖", content_type="text/html")


async def _handle_faq_problem_new(_: Request) -> Response:
    """Handle faq problem new."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_faq_problem_new")
    return web.Response(text="🤖", content_type="text/html")


async def _handle_active_discovery(_: Request) -> Response:
    """Handle active discovery."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_active_discovery")
    return web.Response(text="🤖", content_type="text/html")


async def _handle_view_wifi(_: Request) -> Response:
    """Handle view WiFi."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_view_wifi")
    return web.Response(text="🤖", content_type="text/html")
