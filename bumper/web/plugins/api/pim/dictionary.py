"""Pim dictionary plugin module."""
import logging
from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin

_LOGGER = logging.getLogger("web_route_pim_dict")


class DictionaryPlugin(WebserverPlugin):
    """Dictionary plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                "/dictionary/getErrDetail",
                _handle_get_err_detail,
            ),
        ]


async def _handle_get_err_detail(_: Request) -> Response:
    """Get error details."""
    try:
        return web.json_response(
            {
                "code": -1,
                "data": [],
                "msg": "This errcode's detail is not exists",
            }
        )
    except Exception as e:
        _LOGGER.error(utils.default_exception_str_builder(e, "during handling request"), exc_info=True)
    raise HTTPInternalServerError
