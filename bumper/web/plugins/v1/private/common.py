"""Common plugin module."""

import base64
from collections.abc import Iterable
import json
import logging

import aiofiles
from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from bumper.db import user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_common_area
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


class CommonPlugin(WebserverPlugin):
    """Common plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}common/checkAPPVersion", _handle_check_app_version),
            web.route("*", f"{BASE_URL}common/checkVersion", _handle_check_version),
            web.route("*", f"{BASE_URL}common/uploadDeviceInfo", _handle_upload_device_info),
            web.route("*", f"{BASE_URL}common/getSystemReminder", _handle_get_system_reminder),
            web.route("*", f"{BASE_URL}common/getConfig", _handle_get_config),
            web.route("*", f"{BASE_URL}common/getUserConfig", _handle_get_user_config),
            web.route("*", f"{BASE_URL}common/getAreas", _handle_get_areas),
            web.route("*", f"{BASE_URL}common/getAreaSupportService", _handle_common_get_area_support_service),
            web.route("*", f"{BASE_URL}common/getAgreementURLBatch", _handle_get_agreement_url_batch),
            web.route("*", f"{BASE_URL}common/getTimestamp", _handle_get_timestamp),
            web.route("*", f"{BASE_URL}common/getBottomNavigateInfoList", _handle_get_bottom_navigate_info_list),
            web.route("*", f"{BASE_URL}common/getAboutBriefItem", _handle_get_about_brief_item),
            web.route("*", f"{BASE_URL}common/getCurrentAreaSupportServiceInfo", handle_get_current_area_support_service_info),
        ]


async def _handle_check_version(_: Request) -> Response:
    """Check version."""
    return response_success_v1(
        {
            "c": None,
            "img": None,
            "r": 0,
            "t": None,
            "u": None,
            "ut": 0,
            "v": None,
        },
    )


async def _handle_check_app_version(_: Request) -> Response:
    """Check app version."""
    return response_success_v1(
        {
            "c": None,
            "downPageUrl": None,
            "img": None,
            "nextAlertTime": None,
            "r": 0,
            "t": None,
            "u": None,
            "ut": 0,
            "v": None,
        },
    )


async def _handle_upload_device_info(_: Request) -> Response:
    """Upload device info."""
    return response_success_v1({"devicePushRegisterResult": "N"})


async def _handle_get_system_reminder(_: Request) -> Response:
    """Get system reminder."""
    return response_success_v1(
        {
            "iosGradeTime": {"iodGradeFlag": "N"},
            "openNotification": {
                "openNotificationContent": None,
                "openNotificationFlag": "N",
                "openNotificationTitle": None,
            },
        },
    )


async def _handle_get_config(request: Request) -> Response:
    """Get config."""
    try:
        data: list[dict[str, str]] = []
        for key in request.query["keys"].split(","):
            if key == "PUBLIC.KEY.CONFIG":
                async with aiofiles.open(bumper_isc.server_cert, "rb") as cert_file:
                    cert_data = await cert_file.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                public_key = cert.public_key().public_bytes(encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo)
                base64_encoded_public_key = base64.b64encode(public_key).decode("utf-8")
                data.append({"key": key, "value": json.dumps({"publicKey": base64_encoded_public_key})})

            elif key == "EMAIL.REGISTER.CONFIG":
                data.append({"key": key, "value": json.dumps({"needVerify": "N"})})
            elif key == "OPEN.APP.CERTIFICATE.CONFIG":
                data.append({"key": key, "value": json.dumps({"ISO27001": "ENABLED", "TUV": "ENABLED"})})
                # data.append({"key": key, "value": json.dumps({"ISO27001": "DISABLED", "TUV": "DISABLED"})})
            elif key == "USER.DATA.COLLECTION":
                data.append({"key": key, "value": "N"})
            elif key == "USER.DEVICE.LIST.CONFIG":
                data.append({"key": key, "value": json.dumps({"showFlag": "N"})})
            elif key == "PRIVACY.CONFIG":
                data.append(
                    {
                        "key": key,
                        "value": json.dumps(
                            [
                                {"key": "PERSONAL_INFO_SHARING", "status": "DISABLED", "url": ""},
                                {"key": "THIRD_PARTY_SDK", "status": "DISABLED", "url": ""},
                            ],
                        ),
                    },
                )
            # TODO: elif key == "FIND.PASSWORD.FAQ.CONF":
            else:
                _LOGGER.warning(f"NEW CONFIG KEY :: {key} :: needs further investigation")
                data.append({"key": key, "value": "Y"})

        return response_success_v1(data)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_get_user_config(request: Request) -> Response:
    """Get user config."""
    try:
        user_dev_id = request.match_info.get("devid", "")
        user = user_repo.get_by_device_id(user_dev_id)
        if user is None:
            _LOGGER.warning(f"No user found for {user_dev_id}")
        else:
            return response_success_v1(
                {
                    "saTraceConfig": {
                        "collectionStatus": "DISABLED",
                        "isTrace": "N",
                        "saUserId": user.userid,
                        "serverUrl": f"https://{bumper_isc.DOMAIN_SEC5}/sa?project=production",
                    },
                },
            )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_get_areas(_: Request) -> Response:
    """Get Areas."""
    try:
        return response_success_v1(get_common_area())
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_common_get_area_support_service(_: Request) -> Response:
    """Get Area Support Service."""
    return response_success_v1({"isSelfHelpRepair": "N"})


async def _handle_get_agreement_url_batch(_: Request) -> Response:
    """Get agreement url batch."""
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    return response_success_v1(
        [
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
        ],
    )


async def _handle_get_timestamp(_: Request) -> Response:
    """Get timestamp."""
    time = utils.get_current_time_as_millis()
    return response_success_v1({"timestamp": time}, time)


async def _handle_get_about_brief_item(_: Request) -> Response:
    """Get about brief item."""
    return response_success_v1([])


async def _handle_get_bottom_navigate_info_list(_: Request) -> Response:
    """Get bottom navigation info list."""
    domain_01 = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    domain_02 = f"https://{bumper_isc.DOMAIN_SEC1}/us"
    return response_success_v1(
        [
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
        ],
    )


async def handle_get_current_area_support_service_info(_: Request) -> Response:
    """Get current area support service info."""
    return response_success_v1(
        {
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
        },
    )
