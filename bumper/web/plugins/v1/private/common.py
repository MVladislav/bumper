"""Common plugin module."""

from datetime import datetime
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request

from bumper.db import user_repo
from bumper.utils import utils
from bumper.utils.account_key import account_public_key
from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, bind
from bumper.web.hosts import wap_host
from bumper.web.static_api import get_common_area

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


#: The config values the app asks for. The value of a key is a string; the
#: ones that carry a document are the json of that document.
CONFIG_VALUES: dict[str, str] = {
    "AREA.CONFIG": json.dumps({"sensitiveDataExportFlag": "N"}),
    "EMAIL.REGISTER.CONFIG": json.dumps({"needVerify": "N"}),
    "FIND.PASSWORD.FAQ.CONF": f"https://{wap_host()}/web/page?no=qp8mz4iv",
    "OPEN.APP.CERTIFICATE.CONFIG": json.dumps({"ISO27001": "ENABLED", "TUV": "ENABLED"}),
    "PASSWORD.STRENGTH.URL": f"https://{wap_host()}/web/page?no=4vkpuvpy",
    "PRIVACY.CONFIG": json.dumps(
        [
            {"key": "PERSONAL_INFO_SHARING", "status": "DISABLED", "url": ""},
            {"key": "THIRD_PARTY_SDK", "status": "DISABLED", "url": ""},
        ],
    ),
    "SUGGESTION.DEFAULT.FLAG": "Y",
    "USER.DATA.COLLECTION": "N",
    "USER.DEVICE.LIST.CONFIG": json.dumps({"showFlag": "N"}),
    "DEVICE.OTP.CONFIG": json.dumps({"ttlSeconds": bumper_isc.DEVICE_OTP_TTL_SECONDS}),
}


@routes.view(f"{BASE_URL}common/checkVersion")
@bind(GL_V1)
async def _handle_check_version(_: Request) -> Any:
    """Check version."""
    return {
        "c": None,
        "img": None,
        "r": 0,
        "t": None,
        "u": None,
        "ut": 0,
        "v": None,
    }


@routes.view(f"{BASE_URL}common/checkAPPVersion")
@bind(GL_V1)
async def _handle_check_app_version(_: Request) -> Any:
    """Check app version."""
    return {
        "c": None,
        "downPageUrl": None,
        "img": None,
        "nextAlertTime": None,
        "r": 0,
        "t": None,
        "u": None,
        "ut": 0,
        "v": None,
    }


@routes.view(f"{BASE_URL}common/uploadDeviceInfo")
@bind(GL_V1)
async def _handle_upload_device_info(request: Request) -> Any:
    """Upload device info."""
    device_id = request.query.get("deviceNum", "")
    device_model = request.query.get("model", "")
    if device_id and device_model and (user := user_repo.get_by_device_id(device_id)) is not None:
        user_repo.set_device_name(user.userid, device_id, device_model)
    return {"devicePushRegisterResult": "N"}


@routes.view(f"{BASE_URL}common/getSystemReminder")
@bind(GL_V1)
async def _handle_get_system_reminder(_: Request) -> Any:
    """Get system reminder."""
    return {
        "iosGradeTime": {"iodGradeFlag": "N"},
        "openNotification": {
            "openNotificationContent": None,
            "openNotificationFlag": "N",
            "openNotificationTitle": None,
        },
    }


@routes.view(f"{BASE_URL}common/getUserDevice")
@bind(GL_V1)
async def _handle_get_user_device(request: Request) -> Any:
    """Get the current app device."""
    device_id = request.match_info.get("devid", "")
    user = user_repo.get_by_device_id(device_id)
    device_ids = user.devices if user is not None else []
    last_login = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    return {
        "userDeviceList": [
            {
                "id": app_device_id,
                "deviceName": user.device_names.get(app_device_id, "Bumper") if user is not None else "Bumper",
                "isCurrentDevice": "Y" if app_device_id == device_id else "N",
                "lastLoginTime": last_login if app_device_id == device_id else "",
                "isTrust": "N",
            }
            for app_device_id in device_ids
        ],
        "helpModule": None,
    }


@routes.view(f"{BASE_URL}common/deleteUserDevice")
@bind(GL_V1)
async def _handle_delete_user_device(request: Request) -> None:
    """Acknowledge a request to remove an app device."""
    user_id = request.query.get("uid", "")
    device_id = request.query.get("userDeviceId", "")
    user = user_repo.get_by_id(user_id)
    if user is not None and device_id in user.devices:
        user_repo.remove_device(user_id, device_id)


@routes.view(f"{BASE_URL}common/getAllServiceInfo")
@bind(GL_V1)
async def _handle_get_all_service_info(_: Request) -> Any:
    """Get the support services available from the local server."""
    return {
        "cnLiveChatInfo": {"isSupport": "N"},
        "zendeskLiveChatInfo": {
            "isSupport": "N",
            "isServiceTime": None,
            "serviceTimeStr": None,
            "accountKey": None,
            "email": None,
            "name": None,
            "preChatFormMap": None,
        },
        "zendeskMessageInfo": {"isSupport": "N", "zendeskStartInfo": None},
        "phoneServiceInfo": {
            "isSupport": "N",
            "isServiceTime": "N",
            "serviceTimeStr": "",
            "phone": "",
            "phones": [],
        },
        "emailInfo": {"isSupport": "N", "email": ""},
        "feedbackInfo": {"isSupport": "N"},
        "salesforceLiveChatInfo": {
            "isSupport": "N",
            "isServiceTime": "N",
            "serviceTimeStr": "",
            "url": "",
            "noServiceType": None,
        },
        "salesforceMessageInfo": {
            "isSupport": "N",
            "isServiceTime": "N",
            "serviceTimeStr": "",
            "url": "",
            "noServiceType": None,
        },
        "intlSalesServiceInfo": {"isSupport": "N", "url": None, "serviceTimeStr": None, "noServiceType": None},
    }


@routes.view(f"{BASE_URL}common/getConfig")
@bind(GL_V1)
async def _handle_get_config(request: Request) -> Any:
    """Get config."""
    data: list[dict[str, str]] = []
    for key in request.query["keys"].split(","):
        value = json.dumps({"publicKey": account_public_key()}) if key == "PUBLIC.KEY.CONFIG" else CONFIG_VALUES.get(key)
        if value is not None:
            data.append({"key": key, "value": value})
        else:
            _LOGGER.warning(f"NEW CONFIG KEY :: {key} :: needs further investigation")
            data.append({"key": key, "value": "Y"})

    return data


@routes.view(f"{BASE_URL}common/getUserConfig")
@bind(GL_V1)
async def _handle_get_user_config(request: Request) -> Any:
    """Get user config."""
    user_dev_id = request.match_info.get("devid", "")
    user = user_repo.get_by_device_id(user_dev_id)
    if user is None:
        _LOGGER.warning(f"No user found for {user_dev_id}")
    else:
        return {
            "saTraceConfig": {
                "collectionStatus": "DISABLED",
                "isTrace": "N",
                "saUserId": user.userid,
                "serverUrl": f"https://{bumper_isc.DOMAIN_SEC5}/sa?project=production",
            },
        }
    raise HTTPInternalServerError


@routes.view(f"{BASE_URL}common/getAreas")
@bind(GL_V1)
async def _handle_get_areas(_: Request) -> Any:
    """Get Areas."""
    return get_common_area()


@routes.view(f"{BASE_URL}common/getAreaSupportService")
@bind(GL_V1)
async def _handle_common_get_area_support_service(_: Request) -> Any:
    """Get Area Support Service."""
    return {"isSelfHelpRepair": "N"}


@routes.view(f"{BASE_URL}common/getAgreementURLBatch")
@bind(GL_V1)
async def _handle_get_agreement_url_batch(_: Request) -> Any:
    """Get agreement url batch."""
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    return [
        {
            "id": "20250123112347_96bf8aa2fe1f6e2659999dd5873b000a",
            "type": "USER",
            "version": "1.10",
            "url": f"{domain}?id=20250123112347_96bf8aa2fe1f6e2659999dd5873b000a&language=EN",
            "force": None,
            "acceptTime": None,
            "updateDesc": "      ",
        },
        {
            "id": "20250220115739_f6ae49bb83f9de656b0d458f1820580c",
            "type": "PRIVACY",
            "version": "1.10",
            "url": f"{domain}?id=20250220115739_f6ae49bb83f9de656b0d458f1820580c&language=EN",
            "force": None,
            "acceptTime": None,
            "updateDesc": (
                "This is a modified (bumper) version of the original application.\n"
                " Use at your own risk. No guarantees are made regarding data security,\n"
                " functionality, or privacy. By using this version, you accept full responsibility for any outcomes."
            ),
        },
    ]


@routes.view(f"{BASE_URL}common/getTimestamp")
@bind(GL_V1.with_time(utils.get_current_time_as_millis()))
async def _handle_get_timestamp(_: Request) -> Any:
    """Get timestamp."""
    time = utils.get_current_time_as_millis()
    return {"timestamp": time}


@routes.view(f"{BASE_URL}common/getAboutBriefItem")
@bind(GL_V1)
async def _handle_get_about_brief_item(_: Request) -> Any:
    """Get about brief item."""
    return []


@routes.view(f"{BASE_URL}common/getBottomNavigateInfoList")
@bind(GL_V1)
async def _handle_get_bottom_navigate_info_list(_: Request) -> Any:
    """Get bottom navigation info list."""
    domain_01 = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    domain_02 = f"https://{bumper_isc.DOMAIN_SEC1}/us"
    return [
        {
            "bgImgUrl": None,
            "defaultImgUrl": f"{domain_01}/2023/05/09/20230509015020_b1503be93bea4cc11d75bf350f3c188d.png",
            "iconId": "20230509015048_e6d8aafd16e80fe0d3ec893be8f40b32",
            "iconName": "Robot",
            "iconType": "ROBOT",
            "lightImgUrl": f"{domain_01}/2023/05/09/20230509015024_8e854006dd2b049460c96dea89604909.png",
            "lightNameRgb": "#005EB8",
            "mediaType": None,
            "mediaUrl": "NULL",
            "positionType": "Robot",
            "tabItemActionUrl": None,
        },
        {
            "bgImgUrl": None,
            "defaultImgUrl": f"{domain_01}/2023/05/09/20230509015030_13ea2faef0d0908af8a3a6486a678eef.png",
            "iconId": "20230509015048_fa825040a65166c17bafdadc718df095",
            "iconName": "Store",
            "iconType": "MALL",
            "lightImgUrl": f"{domain_01}/2023/05/09/20230509015033_9af971ffdf084a11b153fd3753418d92.png",
            "lightNameRgb": "#005EB8",
            "mediaType": None,
            "mediaUrl": "NULL",
            "positionType": "Store",
            "tabItemActionUrl": f"{domain_02}?utm_source=ecovacsGlobalApp&utm_medium=Appshopclick_US&utm_campaign=Menu_US",
        },
        {
            "bgImgUrl": None,
            "defaultImgUrl": f"{domain_01}/2023/05/09/20230509015037_d8126eaa65d38935cbb6283cca2a0519.png",
            "iconId": "20230509015048_04732bdb41f45b3510e9fd0adc6dc008",
            "iconName": "Mine",
            "iconType": "MINE",
            "lightImgUrl": f"{domain_01}/2023/05/09/20230509015041_0e8b6fb3428ae8aac6a0c04a81e26525.png",
            "lightNameRgb": "#005EB8",
            "mediaType": None,
            "mediaUrl": "NULL",
            "positionType": "Mine",
            "tabItemActionUrl": None,
        },
    ]


@routes.view(f"{BASE_URL}common/getCurrentAreaSupportServiceInfo")
@bind(GL_V1)
async def handle_get_current_area_support_service_info(_: Request) -> Any:
    """Get current area support service info."""
    return {
        "intlFeedbackStartInfo": {
            "emailStartInfo": None,
            "feedbackType": None,
            "phoneStartInfo": None,
            "zendeskStartInfo": {
                "appId": None,
                "clientId": None,
                "feedbackTags": ["tag_area_de"],
                "jwtIdentity": None,
                "zendeskUrl": None,
            },
        },
        "liveChatInfo": {
            "accountKey": None,
            "email": None,
            "endTime": None,
            "isService": None,
            "isSupport": None,
            "name": None,
            "preChatFormMap": {"emailStatus": "0", "nameStatus": "0", "phoneStatus": "0"},
            "serviceTimeEndStr": "00:00",
            "serviceTimeStartStr": "00:00",
            "serviceTimeStr": "Hi, we have no working hours. You can checkout GitHub project page for more info.",
            "startTime": "00:00",
        },
        "officialWebSite": None,
        "phoneServiceInfo": {
            "email": "bumper@home.local",
            "phone": "0000-0000000",
            "phoneAvailableTime": "Monday-Friday 9 AM - 6 PM\r\n(Public holidays excepted)",
            "phoneAvailable": "N",
            "url": f"https://{bumper_isc.DOMAIN_SEC}",
        },
        "salesforceLiveChat": None,
        "emailInfo": {"isSupport": "N", "email": "bumper@home.local"},
    }
