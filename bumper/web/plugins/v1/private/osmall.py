"""OS mall plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class OsMallPlugin(WebserverPlugin):
    """OS mall plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}osmall/getCountryConfig", _handle_get_country_config),
            web.route("*", f"{BASE_URL}osmall/index/getLayout", _handle_get_layout),
            web.route("*", f"{BASE_URL}osmall/index/getBannerList", _handle_get_banner_list),
            web.route("*", f"{BASE_URL}osmall/index/getGoodsCategory", _handle_get_goods_category),
            web.route("*", f"{BASE_URL}osmall/index/getConfNetRobotPartsGoods", _handle_get_conf_net_robot_parts_goods),
            web.route("*", f"{BASE_URL}osmall/index/getRecommendGoods", _handle_get_recommend_goods),
            web.route("*", f"{BASE_URL}osmall/proxy/my/get-user-center-coupon-list", _handle_get_user_center_coupon_list),
            web.route("*", f"{BASE_URL}osmall/proxy/my/get-my-coupon", _handle_get_my_coupon),
            web.route(
                "*",
                f"{BASE_URL}osmall/proxy/coupon-send-activity/get-customer-coupon-send-activity-coupon",
                _handle_get_customer_coupon_send_activity_coupon,
            ),
            web.route("*", f"{BASE_URL}osmall/proxy/cart/get-count", _handle_get_count),
            web.route("*", f"{BASE_URL}osmall/proxy/order/list", _handle_order_list),
            web.route("*", f"{BASE_URL}osmall/proxy/product/material-accessory-list", _handle_material_accessory_list),
            web.route("*", f"{BASE_URL}osmall/proxy/v2/web/benefit/get-benefits", _handle_v2_get_benefits),
            web.route("*", f"{BASE_URL}osmall/proxy/v2/web/payment-icon/index", _handle_v2_payment_icon_index),
        ]


async def _handle_get_country_config(request: Request) -> Response:
    """Get country config."""
    return response_success_v1(
        {
            "defaultLang": request.match_info.get("country", "EN").upper(),
            "openNative": "Y",
            "wapMallUrl": "",
        },
    )


async def _handle_get_layout(_: Request) -> Response:
    """Get layout."""
    return response_success_v1(
        {
            "bgColorNo": "",
            "bgImgUrlBenefit": "",
            "bgImgUrlNv": "",
            "indexId": "20220929111910_9f988dd276fec8ecaedb5f83bbe227fb",
            "indexItemList": [
                {"moduleType": "TOP_BENEFIT"},
                {"moduleType": "TOP_BANNER"},
                {"moduleType": "GOODS_CATEGORY"},
                {"moduleType": "ACCESSORY_RECOMMEND"},
                {"moduleType": "GOODS_RECOMMEND"},
                {"moduleType": "OFFICIAL_BENEFIT"},
                {"moduleType": "SAFE_PAYMENT"},
            ],
        },
    )


async def _handle_get_banner_list(_: Request) -> Response:
    """Get banner list."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return response_success_v1(
        {
            "bannerInfoList": [
                {
                    "adInfo": None,
                    "bannerType": "GOODS",
                    "goodsInfo": {
                        "buyFlag": "N",
                        "goodsId": "243",
                        "goodsSubTitle": None,
                        "goodsTitle": None,
                        "goodsType": "main_goods",
                        "imgUrl": f"{domain}/2023/10/12/20231012043300_c9c28f83f20fcbdd473042e2fe1aae80.jpg",
                        "mediaType": None,
                        "mediaUrl": None,
                    },
                },
                {
                    "adInfo": {
                        "adId": "20231008031415_3d397f051ae2db32230d1c015d04020c",
                        "adName": "DE-X2 OMNI-white",
                        "clickAction": 3,
                        "clickUri": "GlobalMainProductDetail",
                        "imgUrl": f"{domain}/2023/10/08/20231008031258_11ed602251f180f6501dfdcbba0ab1ad.jpg",
                        "mediaType": None,
                        "mediaUrl": None,
                        "paramsJson": '{"goodsId":"271"}',
                    },
                    "bannerType": "AD",
                    "goodsInfo": None,
                },
                {
                    "adInfo": {
                        "adId": "20220929111324_2cdf4a4c07e692b09369a207aab224b8",
                        "adName": "DE-耗材 日常banner",
                        "clickAction": 3,
                        "clickUri": "GlobalAccessoryList",
                        "imgUrl": f"{domain}/2023/08/02/20230802070513_b8db717e7bc8d5e0583bb28a0ea37c23.jpg",
                        "mediaType": None,
                        "mediaUrl": None,
                        "paramsJson": None,
                    },
                    "bannerType": "AD",
                    "goodsInfo": None,
                },
            ],
        },
    )


async def _handle_get_goods_category(_: Request) -> Response:
    """Get goods category."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return response_success_v1(
        {
            "categoryList": [
                {
                    "categoryId": "deebot",
                    "categoryImgUrl": f"{domain}/2022/09/29/20220929102735_3f3c7c2e901a331e0b67ca492fdc3c6a.png",
                    "categoryName": "DEEBOT",
                    "categoryPageTopImgUrl": f"{domain}/2022/09/29/20220929102846_1049b38781c4873ddce718ba7e5c18b8.jpg",
                    "categorySubTitle": "Tomorrow's robots today",
                },
                {
                    "categoryId": "winbot",
                    "categoryImgUrl": f"{domain}/2022/09/29/20220929102922_3034e697186933d61dfef1cbd9c23795.png",
                    "categoryName": "WINBOT",
                    "categoryPageTopImgUrl": f"{domain}/2022/09/29/20220929102913_7b64ef5036d146b9c7425f52eb6e31fa.jpg",
                    "categorySubTitle": "Spotless windows, so simple, so clean",
                },
                {
                    "categoryId": "atmobot",
                    "categoryImgUrl": f"{domain}/2022/10/22/20221022141810_84db4431bf3a5d23e2046f6c7e8d4c16.png",
                    "categoryName": "AIRBOT",
                    "categoryPageTopImgUrl": f"{domain}/2022/10/22/20221022142252_3db74870acc2a1f16052714ba00cdd2b.jpg",
                    "categorySubTitle": "A BREAKTHROUGH IN AIR CLEANING",
                },
                {
                    "categoryId": "accessory",
                    "categoryImgUrl": f"{domain}/2022/09/29/20220929103036_2e6c9f31a0df1d2e286492fdc1ca4253.png",
                    "categoryName": "ACCESSORIES",
                    "categoryPageTopImgUrl": f"{domain}/2022/12/13/20221213024206_bdbe94f753316a1e779f0d36800b8ab2.jpg",
                    "categorySubTitle": "Find the right accessories for your DEEBOT",
                },
                {
                    "categoryId": "goat",
                    "categoryImgUrl": f"{domain}/2023/03/29/20230329125208_fad7fc1e678b4f55a7520b6e52ad96ee.png",
                    "categoryName": "GOAT",
                    "categoryPageTopImgUrl": f"{domain}/2023/03/29/20230329125218_bc88e13645ee1538bade4f7618719e35.jpg",
                    "categorySubTitle": "A CLASS OF ITS OWN",
                },
            ],
        },
    )


async def _handle_get_conf_net_robot_parts_goods(_: Request) -> Response:
    """Get conf net robot pars goods."""
    return response_success_v1({})


async def _handle_get_recommend_goods(_: Request) -> Response:
    """Get recommend goods."""
    return response_success_v1({"goodsList": [], "materialNo": None, "mid": None, "nickName": None})


async def _handle_get_user_center_coupon_list(_: Request) -> Response:
    """Get user center coupon list."""
    return response_success_v1([])


async def _handle_get_my_coupon(_: Request) -> Response:
    """Get my coupon."""
    return response_success_v1({"available": [], "used": [], "invalidated": []})


async def _handle_get_customer_coupon_send_activity_coupon(_: Request) -> Response:
    """Get customer coupon send activity coupon."""
    return response_success_v1([])


async def _handle_get_count(_: Request) -> Response:
    """Get count."""
    return response_success_v1({"item_count": 0.0})


async def _handle_order_list(_: Request) -> Response:
    """Order list."""
    return response_success_v1(
        {
            "list": [],
            "page_data": {
                "current_page": 1.0,
                "list_count": 10.0,
                "total_count": 0.0,
                "total_page": 0.0,
            },
        },
    )


async def _handle_material_accessory_list(_: Request) -> Response:
    """Material accessory list."""
    return response_success_v1([])


async def _handle_v2_get_benefits(_: Request) -> Response:
    """Get benefits."""
    return response_success_v1([])


async def _handle_v2_payment_icon_index(_: Request) -> Response:
    """Payment icon index."""
    return response_success_v1([])
