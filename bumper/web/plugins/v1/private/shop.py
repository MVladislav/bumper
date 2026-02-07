"""Shop plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class ShopPlugin(WebserverPlugin):
    """Shop plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}shop/getCnWapShopConfig", _handle_get_cn_wap_shop_config),
        ]


async def _handle_get_cn_wap_shop_config(_: Request) -> Response:
    """Get cn wap shop config."""
    return response_success_v1(
        {
            "myShopShowFlag": "N",
            "myShopUrl": "",
            "shopIndexShowFlag": "N",
            "shopIndexUrl": "",
        },
    )
