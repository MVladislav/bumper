"""Photo plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v3

_LOGGER = logging.getLogger(__name__)


class PhotoPlugin(WebserverPlugin):
    """Photo plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/photo/list", _handle_photo_list),
        ]


async def _handle_photo_list(_: Request) -> Response:
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_photo_list")
    return response_success_v3(data=None, result_key=None, include_success=True)
