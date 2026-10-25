"""Discover plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils import utils
from bumper.web.envelope import GL_V1, bind
from bumper.web.payloads import discover_labels

from . import BASE_URL

routes = web.RouteTableDef()


@routes.get(f"{BASE_URL}discover/info/getLabelList")
@bind(GL_V1)
async def _handle_get_label_list(_: Request) -> Any:
    """Get label list."""
    return {"labelList": discover_labels()}


@routes.get(f"{BASE_URL}discover/info/getAllInfoPage")
@bind(GL_V1)
async def _handle_get_all_info_page(_: Request) -> Any:
    """Get all info page."""
    utils.default_log_warn_not_impl("_handle_get_all_info_page")
    return None
