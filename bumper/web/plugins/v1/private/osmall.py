"""OS mall plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, bind
from bumper.web.payloads import shop_banner_list, shop_category_list, shop_layout, shop_recommend_goods

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}osmall/getCountryConfig")
@bind(GL_V1)
async def _handle_get_country_config(request: Request) -> Any:
    """Get country config."""
    language = request.match_info.get("language", bumper_isc.ECOVACS_DEFAULT_COUNTRY_LANG)
    return {
        "defaultLang": language.upper(),
        "openNative": "Y",
        "wapMallUrl": "",
    }


@routes.view(f"{BASE_URL}osmall/index/getLayout")
@bind(GL_V1)
async def _handle_get_layout(_: Request) -> Any:
    """Get layout."""
    return shop_layout(
        [
            "TOP_BENEFIT",
            "TOP_BANNER",
            "GOODS_CATEGORY",
            "ACCESSORY_RECOMMEND",
            "GOODS_RECOMMEND",
            "OFFICIAL_BENEFIT",
            "SAFE_PAYMENT",
        ],
    )


@routes.view(f"{BASE_URL}osmall/index/getBannerList")
@bind(GL_V1)
async def _handle_get_banner_list(_: Request) -> Any:
    """Get banner list."""
    return shop_banner_list()


@routes.view(f"{BASE_URL}osmall/index/getGoodsCategory")
@bind(GL_V1)
async def _handle_get_goods_category(_: Request) -> Any:
    """Get goods category."""
    return shop_category_list()


@routes.view(f"{BASE_URL}osmall/index/getConfNetRobotPartsGoods")
@bind(GL_V1)
async def _handle_get_conf_net_robot_parts_goods(_: Request) -> Any:
    """Get conf net robot pars goods."""
    return {}


@routes.view(f"{BASE_URL}osmall/index/getRecommendGoods")
@bind(GL_V1)
async def _handle_get_recommend_goods(_: Request) -> Any:
    """Get recommend goods."""
    return shop_recommend_goods()


@routes.view(f"{BASE_URL}osmall/proxy/my/get-user-center-coupon-list")
@bind(GL_V1)
async def _handle_get_user_center_coupon_list(_: Request) -> Any:
    """Get user center coupon list."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/my/get-my-coupon")
@bind(GL_V1)
async def _handle_get_my_coupon(_: Request) -> Any:
    """Get my coupon."""
    return {"available": [], "used": [], "invalidated": []}


@routes.view(f"{BASE_URL}osmall/proxy/coupon-send-activity/get-customer-coupon-send-activity-coupon")
@bind(GL_V1)
async def _handle_get_customer_coupon_send_activity_coupon(_: Request) -> Any:
    """Get customer coupon send activity coupon."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/cart/get-count")
@bind(GL_V1)
async def _handle_get_count(_: Request) -> Any:
    """Get count."""
    return {"item_count": 0.0}


@routes.view(f"{BASE_URL}osmall/proxy/order/list")
@bind(GL_V1)
async def _handle_order_list(_: Request) -> Any:
    """Order list."""
    return {
        "list": [],
        "page_data": {
            "current_page": 1.0,
            "list_count": 10.0,
            "total_count": 0.0,
            "total_page": 0.0,
        },
    }


@routes.view(f"{BASE_URL}osmall/proxy/product/material-accessory-list")
@bind(GL_V1)
async def _handle_material_accessory_list(_: Request) -> Any:
    """Material accessory list."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/v2/web/benefit/get-benefits")
@bind(GL_V1)
async def _handle_v2_get_benefits(_: Request) -> Any:
    """Get benefits."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/v2/web/payment-icon/index")
@bind(GL_V1)
async def _handle_v2_payment_icon_index(_: Request) -> Any:
    """Payment icon index."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/v2/web/express-icon/index")
@bind(GL_V1)
async def _handle_v2_express_icon_index(_: Request) -> Any:
    """Express icon index."""
    return []


@routes.view(f"{BASE_URL}osmall/proxy/product/get-bonus-points")
@bind(GL_V1)
async def _handle_get_bonus_points(request: Request) -> Any:
    """Get bonus points for products."""
    return {
        product_id: {
            "bonus_points": 0.0,
            "distribution_multiple": 0.0,
            "distribution_multiple_up": 0.0,
            "description": "",
        }
        for product_id in request.query.get("ids", "").split(",")
        if product_id
    }


@routes.view(f"{BASE_URL}osmall/proxy/go/marketing/common/v1/price-activity/get-product-tag")
@bind(GL_V1)
async def _handle_get_product_tags(request: Request) -> Any:
    """Get price activity tags for products."""
    product_ids = request.query.get("product_ids", "").split(",")
    return {
        "list": [{"product_id": float(product_id), "show_tag": False} for product_id in product_ids if product_id.isdigit()],
    }
