"""Basis plugin module."""

from collections.abc import Iterable
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v4

_LOGGER = logging.getLogger(__name__)


class BasisPlugin(WebserverPlugin):
    """Basis plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/basis/dc/get-by-area", _handle_get_by_area),
        ]


async def _handle_get_by_area(request: Request) -> Response:
    """Get by area."""
    try:
        area_code = request.query.get("area", bumper_isc.ECOVACS_DEFAULT_COUNTRY).lower()
        code = 0
        data_str = "data"
        data: dict[str, Any] | str = {"dc": utils.get_dc_code(area_code)}

        if area_code not in utils.get_area_code_map():
            code = 4000
            data_str = "msg"
            msg_list = '", "'.join(utils.get_area_code_map().keys())
            data = f'area: area must be one of the following: "{msg_list}"'

        return response_success_v4(data, code, data_str)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError
