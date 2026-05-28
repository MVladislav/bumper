"""Discover plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class DiscoverPlugin(WebserverPlugin):
    """Discover plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("GET", f"{BASE_URL}discover/info/getLabelList", _handle_get_label_list),
            web.route("GET", f"{BASE_URL}discover/info/getAllInfoPage", _handle_get_all_info_page),
        ]


async def _handle_get_label_list(_: Request) -> Response:
    """Get label list."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_get_label_list")
    return response_success_v1(None)


async def _handle_get_all_info_page(_: Request) -> Response:
    """Get all info page."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_get_all_info_page")
    return response_success_v1(None)
