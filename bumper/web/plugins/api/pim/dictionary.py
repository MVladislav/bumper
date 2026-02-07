"""Pim dictionary plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_err_detail
from bumper.web.utils.response_helper import response_success_v3


class DictionaryPlugin(WebserverPlugin):
    """Dictionary plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/dictionary/getErrDetail", _handle_get_err_detail),
        ]


async def _handle_get_err_detail(_: Request) -> Response:
    """Get error details."""
    return response_success_v3(code=0, msg_key="msg", msg="success", data_key="data", data=get_err_detail(), result_key=None)
