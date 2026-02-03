"""User setting plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL


class UserSettingPlugin(WebserverPlugin):
    """User setting plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}userSetting/getSuggestionSetting", _handle_get_suggestion_setting),
            web.route("*", f"{BASE_URL}userSetting/getMsgReceiveSetting", handle_get_msg_receive_setting),
            web.route("*", f"{BASE_URL}userSetting/saveUserSetting", _handle_save_user_setting),
        ]


async def _handle_get_suggestion_setting(_: Request) -> Response:
    """Get suggestion setting."""
    activity_sub_title = "Allow to receive notification including membership benefits, product and consumable recommendations."
    return response_success_v1(
        {
            "acceptSuggestion": "N",
            "itemList": [
                {
                    "name": "Notification",
                    "settingKey": "ACTIVITY",
                    "subTitle": activity_sub_title,
                    "val": "N",
                },
                {
                    "name": "Allow to Receive Recommendation",
                    "settingKey": "APP_RECOMMEND",
                    "subTitle": "Receive operation instructions and product recommendations in the advertising wanted.",
                    "val": "N",
                },
                {
                    "name": "Promotions/Offers/Events",
                    "settingKey": "MARKETING",
                    "subTitle": None,
                    "val": "N",
                },
                {
                    "name": "User Surveys",
                    "settingKey": "QUESTIONNAIRE",
                    "subTitle": None,
                    "val": "N",
                },
                {
                    "name": "Product Upgrade/User Help",
                    "settingKey": "INTRODUCTION",
                    "subTitle": None,
                    "val": "N",
                },
                {
                    "name": "E-mail",
                    "settingKey": "EMAIL",
                    "subTitle": "Receive operation instructions and product recommendations by e-mail",
                    "val": "N",
                },
            ],
            "userPersonalization": {
                "settingKey": "PERSONALIZATIONIZATION_ADVERTISING",
                "name": None,
                "val": "N",
                "url": f"https://{bumper_isc.DOMAIN_SEC3}/web/page?no=tye52bsd",
            },
        },
    )


async def handle_get_msg_receive_setting(_: Request) -> Response:
    """Get msg receive setting."""
    return response_success_v1(
        {
            "list": [
                {
                    "name": "Promotion messages",
                    "openOrClose": "Y",
                    "settingType": "ACTIVITY",
                },
                {
                    "name": "Service notifications",
                    "openOrClose": "Y",
                    "settingType": "SERVICE_NOTIFICATION",
                },
                {
                    "name": "Customer service messages",
                    "openOrClose": "Y",
                    "settingType": "CUSTOMER_SERVICE",
                },
            ],
        },
    )


async def _handle_save_user_setting(_: Request) -> Response:
    """Save user setting."""
    # TODO: check what's needed to be implemented
    utils.default_log_warn_not_impl("_handle_save_user_setting")
    return response_success_v1(None)
