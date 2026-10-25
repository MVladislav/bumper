"""User setting plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.db import user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.context import claimed_userid
from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}userSetting/getUserAccountSetting")
@bind(GL_V1)
async def _handle_get_user_account_setting(request: Request) -> Any:
    """Get user account settings."""
    user = user_repo.get_by_id(claimed_userid(request) or "")
    device_verification = user.device_verification if user is not None else "DISABLED"
    backup_email = user.backup_email if user is not None else None
    return {"deviceVerification": device_verification, "backUpEmail": backup_email}


@routes.view(f"{BASE_URL}userSetting/modifyUserAccountSetting")
@bind(GL_V1)
async def _handle_modify_user_account_setting(request: Request) -> None:
    """Change one account setting of the caller."""
    user_id = claimed_userid(request)
    setting_key = request.query.get("settingKey", "")
    setting_value = request.query.get("settingValue", "")
    _LOGGER.debug(f"Account setting changed :: {setting_key} = {setting_value}")
    if user_id is not None and setting_key == "DEVICE_VERIFY" and setting_value in {"ENABLED", "DISABLED"}:
        user_repo.set_device_verification(user_id, setting_value)


@routes.view(f"{BASE_URL}userSetting/getSuggestionSetting")
@bind(GL_V1)
async def _handle_get_suggestion_setting(_: Request) -> Any:
    """Get suggestion setting."""
    activity_sub_title = "Allow to receive notification including membership benefits, product and consumable recommendations."
    return {
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
    }


@routes.view(f"{BASE_URL}userSetting/getMsgReceiveSetting")
@bind(GL_V1)
async def handle_get_msg_receive_setting(_: Request) -> Any:
    """Get msg receive setting."""
    return {
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
    }


@routes.view(f"{BASE_URL}userSetting/saveUserSetting")
@bind(GL_V1)
async def _handle_save_user_setting(request: Request) -> Any:
    """Save user setting."""
    utils.default_log_warn_not_impl("_handle_save_user_setting")
    _LOGGER.debug(f"User setting saved :: {await request.text()}")
    return None
