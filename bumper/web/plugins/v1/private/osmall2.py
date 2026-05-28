"""OS mall2 plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class OsMall2Plugin(WebserverPlugin):
    """OS mall2 plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}osmall2/index/getLayout", _handle_get_layout),
        ]


async def _handle_get_layout(_: Request) -> Response:
    """Get Layout."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_get_layout")
    return response_success_v1(
        {
            "bgColorNo": "",
            "bgImgUrlBenefit": "",
            "bgImgUrlNv": "",
            "indexId": "20220929111910_9f988dd276fec8ecaedb5f83bbe227fb",
            "indexItemList": [
                {"moduleType": "TOP_BANNER"},
                {"moduleType": "CATEGORY"},
                {"moduleType": "PRODUCT_POSTER"},
                {"moduleType": "ACTIVITY_CARD"},
                {"moduleType": "BENEFIT"},
                {"moduleType": "PAYMENT"},
                {"moduleType": "EXPRESS"},
                {"moduleType": "RECOMMEND_PRODUCT"},
                {"moduleType": "RECOMMEND_CONSUMABLE"},
                {"moduleType": "ACTIVITY_ZONE"},
                {"moduleType": "INFO"},
                {"moduleType": "BAND"},
            ],
        },
    )
