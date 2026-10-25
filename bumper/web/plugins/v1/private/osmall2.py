"""OS mall2 plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


_INDEX_ID = "20251105163649_63199af1835f121fafb4e21477e52f0b"
_INDEX_MODULES: list[dict[str, str]] = [
    {"moduleType": "TOP_BANNER", "moduleId": "20251105163649_d889fda1563c6b53569cd3ef841cc22c"},
    {"moduleType": "CATEGORY", "moduleId": "20251105163649_0ff2cda31530c0aa31d68724c7b7e42f"},
    {"moduleType": "RECOMMEND_PRODUCT", "moduleId": "20251105163649_abed614fa20f9fb0291ef0838c347c90"},
    {"moduleType": "ACTIVITY_ZONE", "moduleId": "20251105163649_fc9e85a2c1e27daea39d59f444ee686e"},
    {"moduleType": "RECOMMEND_CONSUMABLE", "moduleId": "20251105163649_63fa1f3ba82438a1067ace44140e4c75"},
    {"moduleType": "INFO", "moduleId": "20251105163649_42f8b844a760db8e3bc5e504446841cc"},
    {"moduleType": "BENEFIT", "moduleId": "20251105163649_62f8e36c05fede08b2ba1c4f3f7381a3"},
    {"moduleType": "PAYMENT", "moduleId": "20251105163649_00d1d3f2315b6aff7787adc4b2ad5674"},
    {"moduleType": "EXPRESS", "moduleId": "20251105163649_7e783fa345c420cda00f31f0e006344d"},
]


@routes.view(f"{BASE_URL}osmall2/index/getLayout")
@bind(GL_V1)
async def _handle_get_layout(request: Request) -> Any:
    """Get the shop layout."""
    accepted = set(request.query.get("acceptedModuleType", "").split(","))
    modules = [module for module in _INDEX_MODULES if not accepted or module["moduleType"] in accepted]
    return {"indexId": _INDEX_ID, "bgImgUrlNv": None, "indexItemList": modules}


@routes.view(f"{BASE_URL}osmall2/index/getTopBannerList")
@bind(GL_V1)
async def _handle_get_top_banner_list(_: Request) -> Any:
    """Get top banner list."""
    return {"adInfoList": []}


@routes.view(f"{BASE_URL}osmall2/index/getRecommendGoods")
@bind(GL_V1)
async def _handle_get_recommend_goods(_: Request) -> Any:
    """Get recommended goods."""
    return {"materialNo": None, "mid": None, "nickName": None, "goodsList": []}


@routes.view(f"{BASE_URL}osmall2/index/geActivityZoneList")
@bind(GL_V1)
async def _handle_get_activity_zone_list(_: Request) -> Any:
    """Get activity zone list."""
    return {"adInfoList": []}


@routes.view(f"{BASE_URL}osmall2/index/articleList")
@bind(GL_V1)
async def _handle_get_article_list(_: Request) -> Any:
    """Get article list."""
    return {"articleList": []}
