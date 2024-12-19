"""User plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import db, utils
from bumper.web import auth_util
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import get_success_response

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


class UserPlugin(WebserverPlugin):
    """User plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                f"{BASE_URL}user/login",
                auth_util.login,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/checkLogin",
                auth_util.login,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/getAuthCode",
                auth_util.get_auth_code,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/logout",
                _logout,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/checkAgreement",
                _handle_check_agreement,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/checkAgreementBatch",
                _handle_check_agreement_batch,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/getUserAccountInfo",
                _handle_get_user_account_info,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/getUserMenuInfo",
                _handle_get_user_menu_info,
            ),
            web.route(
                "*",
                f"{BASE_URL}/user/getMyUserMenuInfo",
                _handle_get_my_user_menu_info,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/getMyUserMenuInfo",
                _handle_get_my_user_menu_info,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/changeArea",
                _handle_change_area,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/queryChangeArea",
                _handle_change_area,
            ),
            web.route(
                "*",
                f"{BASE_URL}user/acceptAgreementBatch",
                _handle_accept_agreement_batch,
            ),
        ]


async def _logout(request: Request) -> Response:
    """Logout."""
    try:
        device_id = request.match_info.get("devid")
        access_token = request.query.get("accessToken")
        if device_id is not None and access_token is not None:
            user = db.user_by_device_id(device_id)
            if user is None:
                _LOGGER.warning(f"No user found for {device_id}")
            elif db.check_token(user.userid, access_token):
                # Deactivate old tokens and authcodes
                db.user_revoke_token(user.userid, access_token)
        return get_success_response(None)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def _handle_get_user_account_info(request: Request) -> Response:
    """Get user account info."""
    try:
        user_device_id = request.match_info.get("devid", "")
        user = db.user_by_device_id(user_device_id)
        if user is None:
            _LOGGER.warning(f"No user found for {user_device_id}")
        else:
            intl_member_info = {
                "availableGeneralIntegral": 0,
                "availableLimitedIntegral": 0,
                "benefitList": [],
                "expiringLimitedPointShowDesc": None,
                "expiringLimitedPoints": None,
                "expiringPointDesc": None,
                "expiringPointExplain": None,
                "expiringPoints": None,
                "frozenIntegral": 0,
                "frozenIntegralTips": "Points will be issued 20 days after order payment. Please wait.",
                "goodsDetailIntegralDesc": "Points will be issued 20 days after order payment. Please wait.",
                "integral": 0,
                "integralDescWapUrl": "https://gl-us-wap.ecovacs.com/web/page?no=hh3yxg4g",
                "intlMemberMallUrl": "https://www.ecovacs.com/us",
                "isCountryOpen": "Y",
                "isLimitedIntegralOpen": "N",
                "isMember": "Y",
                "levelName": "VIP1",
                "remainingDay": None,
                "vipLevelIconUrl": "https://gl-us-pub.ecovacs.com/public/220628/d01e939518354ee0af5c88a5269e27d8.png",
            }

            return get_success_response(
                {
                    "email": "null@null.com",
                    "hasMobile": "N",
                    "hasPassword": "Y",
                    "headIco": "",
                    "intlMemberInfo": intl_member_info,
                    "loginName": user.username,
                    "mobile": None,
                    "mobileAreaNo": None,
                    "nickname": "",
                    "obfuscatedMobile": None,
                    "thirdLoginInfoList": [{"accountType": "WeChat", "hasBind": "N"}],
                    "uid": user.userid,
                    "userName": user.username,
                    "userShowName": user.username,
                },
            )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_check_agreement(request: Request) -> Response:
    """Check agreement."""
    app_type = request.match_info.get("apptype", "")
    data = []
    domain = "https://gl-us-wap.ecovacs.com/content/agreement"
    if "global_" in app_type:
        data = [
            {
                "force": "N",
                "id": "20180804040641_7d746faf18b8cb22a50d145598fe4c90",
                "type": "USER",
                "url": f"{domain}?id=20180804040641_7d746faf18b8cb22a50d145598fe4c90&language=EN",
                "version": "1.01",
            },
            {
                "force": "N",
                "id": "20180804040245_4e7c56dfb7ebd3b81b1f2747d0859fac",
                "type": "PRIVACY",
                "url": f"{domain}?id=20180804040245_4e7c56dfb7ebd3b81b1f2747d0859fac&language=EN",
                "version": "1.01",
            },
        ]
    return get_success_response(data)


async def _handle_check_agreement_batch(_: Request) -> Response:
    """Check agreement batch."""
    return get_success_response(
        {
            "agreementList": [],
            "reAcceptFlag": None,
            "userAcceptRecord": [
                {
                    "acceptTime": 1681542125538,
                    "force": None,
                    "id": "20230403095818_78798528690d2307bd692c0b624909f9",
                    "type": "USER",
                    "updateDesc": None,
                    "url": None,
                    "version": "1.03",
                },
                {
                    "acceptTime": 1681542128770,
                    "force": None,
                    "id": "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
                    "type": "PRIVACY",
                    "updateDesc": None,
                    "url": None,
                    "version": "1.07",
                },
            ],
        },
    )


async def _handle_get_user_menu_info(_: Request) -> Response:
    """Get user menu info."""
    domain = "https://gl-us-pub.ecovacs.com/upload/global"
    return get_success_response(
        [
            {
                "menuItems": [
                    {
                        "clickAction": 1,
                        "clickUri": "https://ecovacs.zendesk.com/hc/en-us",
                        "menuIconUrl": f"{domain}/2019/12/16/2019121603180741b73907046e742b80e8fe4a90fe2498.png",
                        "menuId": "20191216031849_4d744630f7ad2f5208a4b8051be61d10",
                        "menuName": "Help & Feedback",
                        "paramsJson": "",
                    },
                ],
                "menuPositionKey": "A_FIRST",
            },
            {
                "menuItems": [
                    {
                        "clickAction": 3,
                        "clickUri": "robotShare",
                        "menuIconUrl": f"{domain}/2019/12/16/2019121603284185e632ec6c5da10bd82119d7047a1f9e.png",
                        "menuId": "20191216032853_5fac4cc9cbd0e166dfa951485d1d8cc4",
                        "menuName": "Share Robot",
                        "paramsJson": "",
                    },
                ],
                "menuPositionKey": "B_SECOND",
            },
            {
                "menuItems": [
                    {
                        "clickAction": 3,
                        "clickUri": "config",
                        "menuIconUrl": f"{domain}/2019/12/16/201912160325324068da4e4a09b8c3973db162e84784d5.png",
                        "menuId": "20191216032545_ebea0fbb4cb02d9c2fec5bdf3371bc2d",
                        "menuName": "Settings",
                        "paramsJson": "",
                    },
                ],
                "menuPositionKey": "C_THIRD",
            },
            {
                "menuItems": [
                    {
                        "clickAction": 1,
                        "clickUri": "https://bumper.ecovacs.com/",
                        "menuIconUrl": f"{domain}/2019/12/16/201912160325324068da4e4a09b8c3973db162e84784d5.png",
                        "menuId": "20191216032545_ebea0fbb4cb02d9c2fec5bdf3371bc2c",
                        "menuName": "Bumper Status",
                        "paramsJson": "",
                    },
                ],
                "menuPositionKey": "D_FOURTH",
            },
        ],
    )


async def _handle_get_my_user_menu_info(_: Request) -> Response:
    """Get my user menu info."""
    domain = "https://gl-us-pub.ecovacs.com/upload/global"
    return get_success_response(
        {
            "menuList": [
                {
                    "menuItems": [
                        {
                            "clickAction": 3,
                            "clickUri": "glOrlderList",
                            "menuIconUrl": f"{domain}/2022/10/10/20221010104231_68dd6755a706e47113b110a6d5ec931a.png",
                            "menuId": "20221010104238_3f41cf9ecc1c44ebd39fc6e77a975067",
                            "menuName": "My Orders",
                            "menuSubName": "",
                            "paramsJson": "",
                            "redDotId": None,
                        },
                        {
                            "clickAction": 1,
                            "clickUri": "https://adv-app.dc-na.ww.ecouser.net/pim/third_party_voice_control.html",
                            "menuIconUrl": f"{domain}/2022/12/14/20221214024053_10124672980fdcd4828fd5cbdf5c87ef.png",
                            "menuId": "20221214024100_207b336dcbcd6b96fb6b2c57fc14f095",
                            "menuName": "Third-party Voice Control",
                            "menuSubName": None,
                            "paramsJson": "",
                            "redDotId": None,
                        },
                        {
                            "clickAction": 3,
                            "clickUri": "helpfbView",
                            "menuIconUrl": f"{domain}/2022/05/10/20220510035541_93dd3bd6a9e4ee67eb4950d710f62ee1.png",
                            "menuId": "20220510035545_505adfaba38be91cd4426a5870173479",
                            "menuName": "Help & Feedback",
                            "menuSubName": None,
                            "paramsJson": "",
                            "redDotId": None,
                        },
                        {
                            "clickAction": 3,
                            "clickUri": "config",
                            "menuIconUrl": f"{domain}/2022/05/10/20220510035629_ac83db12a8ff972f1f611e8a549c18ab.png",
                            "menuId": "20220510035647_d2c7960a95f47b85158a0128ef562020",
                            "menuName": "Settings",
                            "menuSubName": None,
                            "paramsJson": "",
                            "redDotId": None,
                        },
                    ],
                    "menuPositionKey": "MY_A",
                },
            ],
        },
    )


async def _handle_change_area(_: Request) -> Response:
    """Change area."""
    return get_success_response({"isNeedReLogin": "N"})


async def _handle_accept_agreement_batch(_: Request) -> Response:
    """Accept agreement batch."""
    return get_success_response(None)
