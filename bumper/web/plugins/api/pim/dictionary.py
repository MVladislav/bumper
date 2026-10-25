"""Pim dictionary plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import LEGACY, bind
from bumper.web.static_api import get_err_detail

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/dictionary/getErrDetail")
@bind(LEGACY.with_code(0).with_data_key("data").with_result(None).with_msg(("msg", "success")))
async def _handle_get_err_detail(_: Request) -> Any:
    """Get error details."""
    return get_err_detail()
