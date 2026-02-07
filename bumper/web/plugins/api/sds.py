"""Sds plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3

_LOGGER = logging.getLogger(__name__)


class SdsPlugin(WebserverPlugin):
    """Sds plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/sds/baidu/audio/getcred", _handle_baidu_audio_getcred),
        ]


async def _handle_baidu_audio_getcred(_: Request) -> Response:
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_baidu_audio_getcred")
    return response_success_v3(data=None, result_key=None, include_success=True)
