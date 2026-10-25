"""Shop plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}shop/getCnWapShopConfig")
@bind(GL_V1)
async def _handle_get_cn_wap_shop_config(_: Request) -> Any:
    """Get cn wap shop config."""
    return {
        "myShopShowFlag": "N",
        "myShopUrl": "",
        "shopIndexShowFlag": "N",
        "shopIndexUrl": "",
    }
