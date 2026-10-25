"""Basis plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import LEGACY_BARE, bind
from bumper.web.static_api import get_timezones

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/basis/time/timezones")
@bind(LEGACY_BARE)
async def _handle_get_timezones(_: Request) -> Any:
    """Get the timezone list."""
    return get_timezones()


@routes.view(f"{PREFIX}/basis/dc/get-by-area")
async def _handle_get_by_area(request: Request) -> Response:
    """Get by area.

    The answer carries the code and the key of the payload, and both depend
    on the request, so the shape is built here.
    """
    area_code = request.query.get("area", bumper_isc.ECOVACS_DEFAULT_COUNTRY).lower()

    if area_code not in utils.get_area_code_map():
        msg_list = '", "'.join(utils.get_area_code_map().keys())
        return web.json_response(
            LEGACY_BARE.with_code(4000).with_data_key("msg").render(f'area: area must be one of the following: "{msg_list}"'),
        )

    return web.json_response(LEGACY_BARE.render({"dc": utils.get_dc_code(area_code)}))
