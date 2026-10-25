"""Rapp plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils import utils
from bumper.web.envelope import LEGACY, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/rapp/sds/user/data/map/get")
@bind(LEGACY.with_result(None))
async def _handle_map_get(_: Request) -> Any:
    """Map get."""
    utils.default_log_warn_not_impl("_handle_user_data_del")
    return {
        "data": {"name": "My Home"},
        "tag": None,
    }


@routes.view(f"{PREFIX}/rapp/sds/user/data/del")
@bind(LEGACY.with_result(None))
async def _handle_user_data_del(_: Request) -> Any:
    """User data del."""
    utils.default_log_warn_not_impl("_handle_user_data_del")
    return None


@routes.view(f"{PREFIX}/rapp/sds/user/data/list")
@bind(LEGACY.with_result(None))
async def _handle_user_data_list(_: Request) -> Any:
    """User data list."""
    utils.default_log_warn_not_impl("_handle_user_data_list")
    return [
        {
            "key": "iwashere",
            "data": None,
            "createTime": utils.get_current_time_as_millis(),
            "updateTime": utils.get_current_time_as_millis(),
        },
    ]
