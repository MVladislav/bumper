"""Rapp plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3


class RappPlugin(WebserverPlugin):
    """Rapp plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/rapp/sds/user/data/map/get", _handle_map_get),
            web.route("*", "/rapp/sds/user/data/del", _handle_user_data_del),
            web.route("*", "/rapp/sds/user/data/list", _handle_user_data_list),
        ]


async def _handle_map_get(_: Request) -> Response:
    """Map get."""
    return response_success_v3(
        result_key=None,
        data={
            "data": {"name": "My Home"},
            "tag": None,
        },
    )


async def _handle_user_data_del(_: Request) -> Response:
    """User data del."""
    return response_success_v3(result_key=None, data=None)


async def _handle_user_data_list(_: Request) -> Response:
    """User data list."""
    return response_success_v3(
        result_key=None,
        data=[
            {
                "key": "iwashere",  # TODO: not know what key it is
                "data": None,
                "createTime": utils.get_current_time_as_millis(),
                "updateTime": utils.get_current_time_as_millis(),
            },
        ],
    )
