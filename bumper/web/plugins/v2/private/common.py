"""Common plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.v1.private.common import handle_get_current_area_support_service_info
from bumper.web.response_utils import response_success_v1

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


class CommonPlugin(WebserverPlugin):
    """Common plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}common/getBottomNavigateInfoList", handle_get_bottom_navigate_info_list),
            web.route("GET", f"{BASE_URL}common/YIKOBasicSetting", _handle_yiko_basic_setting),
            web.route("*", f"{BASE_URL}common/getCurrentAreaSupportServiceInfo", handle_get_current_area_support_service_info),
        ]


async def handle_get_bottom_navigate_info_list(_: Request) -> Response:
    """Get bottom navigation info list."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return response_success_v1(
        {
            "bgImgUrl": None,
            "navigateInfoResponseList": [
                {
                    "iconId": "20241122063707_19a7b3237fe6ef5a2f082063c7241d7a",
                    "iconName": "Robot",
                    "iconType": "ROBOT",
                    "defaultImgUrl": f"{domain}/2024/11/04/20241104074310_add0cf9b618994adecd48a2ada9289c0.png",
                    "lightImgUrl": f"{domain}/2024/11/04/20241104074317_32d5a6c83ad298b59e45343316fb9311.png",
                    "lightNameRgb": "#253746",
                    "mediaType": None,
                    "mediaUrl": None,
                    "positionType": "Robot",
                    "tabItemActionUrl": None,
                    "bgImgUrl": None,
                    "defaultNameRgb": "#B1C4DE",
                },
                {
                    "iconId": "20241122063707_ee95e86e7f0e617bd235490a6bd73d8a",
                    "iconName": "Store",
                    "iconType": "MALL",
                    "defaultImgUrl": f"{domain}/2024/11/04/20241104075006_c0acb1320aa6ee4cf4150012bd394471.png",
                    "lightImgUrl": f"{domain}/2024/11/04/20241104075015_54a2f48ee2ca61104c4b9d541b56a740.png",
                    "lightNameRgb": "#253746",
                    "mediaType": None,
                    "mediaUrl": None,
                    "positionType": "Store",
                    "tabItemActionUrl": None,
                    "bgImgUrl": None,
                    "defaultNameRgb": "#B1C4DE",
                },
                {
                    "iconId": "20241122063707_f44f7914d334ea6a33ba9735fac86ed7",
                    "iconName": "Discover",
                    "iconType": "DISCOVER",
                    "defaultImgUrl": f"{domain}/2024/11/04/20241104080407_3f320d885453c106e58bfd2da305f644.png",
                    "lightImgUrl": f"{domain}/2024/11/04/20241104080420_1eb0a172dc65e6bb6acd676f8e31be4c.png",
                    "lightNameRgb": "#253746",
                    "mediaType": None,
                    "mediaUrl": None,
                    "positionType": "Discovery",
                    "tabItemActionUrl": None,
                    "bgImgUrl": None,
                    "defaultNameRgb": "#B1C4DE",
                },
                {
                    "iconId": "20241122063707_4b19facb3f136f95b23f81f2d72272dc",
                    "iconName": "Me",
                    "iconType": "MINE",
                    "defaultImgUrl": f"{domain}/2024/11/04/20241104075720_cc63447c6ea13b4b51093230415f6851.png",
                    "lightImgUrl": f"{domain}/2024/11/04/20241104075733_e1ef1d2f744347ac0b8af09508fa0299.png",
                    "lightNameRgb": "#253746",
                    "mediaType": None,
                    "mediaUrl": None,
                    "positionType": "Mine",
                    "tabItemActionUrl": None,
                    "bgImgUrl": None,
                    "defaultNameRgb": "#B1C4DE",
                },
            ],
            "robotBackgroundImg": None,
            "robotBaseArcShapedImg": None,
            "onLineBtnGradientsBackground": None,
            "onLineBtnInsideText": None,
            "onLineBtnInsideOutline": None,
            "onLineBtnOutsideOutline": None,
            "offLineBtn": None,
            "otherElements": None,
            "robotPersonalizationConfigSwitch": "N",
        },
    )


async def _handle_yiko_basic_setting(_: Request) -> Response:
    return response_success_v1(None)
