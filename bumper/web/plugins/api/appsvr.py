"""Appsvr plugin module."""

import asyncio
from collections.abc import Mapping
import json
import logging
import secrets
from typing import Any
from urllib.parse import parse_qs, urlparse

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.db import bot_repo, identity
from bumper.mqtt.helper_bot import MQTTCommandModel
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_service
from bumper.web.context import claimed_userid, read_body
from bumper.web.envelope import LEGACY, LEGACY_BARE, TODO_RET, TODO_RET_UNKNOWN, ApiError, bind
from bumper.web.hosts import api_host, pim_host
from bumper.web.operations import Operation, dispatch
from bumper.web.payloads import codepush_update_check, config_faq, device_list, service_list
from bumper.web.static_api import (
    get_code_push_config,
    get_config_groups_response,
    get_config_groups_robot,
    get_product_category,
    get_product_iot_map,
)
from bumper.web.utils.files import file_in_dir
from bumper.web.utils.models import BumperUser

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/appsvr/oauth_callback")
@bind(LEGACY)
async def _handle_oauth_callback(request: Request) -> Any:
    """Answer the callback of the login with the tokens of the user.

    The app sends the auth code of the login and receives the access token,
    the refresh token and the expiry of the access token.
    """
    return await auth_service.oauth_callback(request)


@routes.view(f"{PREFIX}/appsvr/oauth/token")
@bind(LEGACY)
async def _handle_oauth_token(request: Request) -> Any:
    """Answer a refresh of the tokens of the user.

    The app sends the refresh token it got from the callback and receives
    the same answer as the callback does.
    """
    return await auth_service.oauth_callback(request)


#: The operations of `app.do`. The shape of the answer belongs to the
#: operation, so the table names the shape every todo answers with.
APP_DO_OPERATIONS: dict[str, Operation] = {}


routes.post(f"{PREFIX}/appsvr/app.do")(dispatch(APP_DO_OPERATIONS, TODO_RET_UNKNOWN))


@routes.view(f"{PREFIX}/appsvr/app/config")
@bind(LEGACY)
async def _handle_app_config(request: Request) -> Any:
    """App config."""
    code = request.query.get("code", "")
    data: list[dict[str, Any]] | None = None
    contenturl = api_host("adv-app", bumper_isc.DOMAIN_MAIN)

    if code == "app_lang_enum":
        data = [
            {
                "resId": "622ee4977404d4518fd575fb",  # pragma: allowlist secret
                "code": "app_lang_enum",
                "name": "APP 语言枚举列表",
                "description": "",
                "type": "json",
                "content": {
                    "ar": "العربية",
                    "cs": "český",
                    "da": "Dansk",
                    "nl": "Nederlands",
                    "zh": "普通话",
                    "zh_cn": "普通话",
                    "zh-hans": "简体中文",
                    "zh-hant": "繁體中文",
                    "en": "English",
                    "en-us": "English(American)",
                    "en-au": "English(Australian)",
                    "en-ca": "English(Canadian)",
                    "en-in": "English(Indian)",
                    "en-gb": "English(United Kingdom)",
                    "et": "Eesti",
                    "he": "עברי",
                    "hu": "Magyar",
                    "id": "Indonesia",
                    "lv": "Latvijas",
                    "lt": "Lietuvos",
                    "no": "Norsk språk",
                    "fa": "فارسی",
                    "pl": "Polski",
                    "pt": "Português",
                    "sv": "Svenska",
                    "hk": "粤語",
                    "tw": "國語",
                    "th": "ไทย",
                    "tr": "Türkçe",
                    "my": "Malay",
                    "de": "Deutsch",
                    "fr": "Français",
                    "es": "Español",
                    "it": "Italiano",
                    "ru": "Pусский",
                    "sk": "Slovenský jazyk",
                    "ko": "한국어",
                    "vn": "Tiếng Việt",
                    "ja": "日本語",
                },
            },
        ]

    elif code == "codepush_config":
        data = get_code_push_config()

    elif code == "base_station_guide":
        data = [
            {
                "resId": "61cd0abe312d7cfc89acf608",  # pragma: allowlist secret
                "code": "base_station_guide",
                "name": "Introduction to AES base stations",  # AES基站介绍
                "description": "",
                "type": "text",
                "content": f"https://{contenturl}/pim/base_station_guide_newton_curi.html?lang=en&defaultLang=en",
            },
        ]

    elif code == "time_zone_list":
        data = [
            {
                "resId": "61a055be6533d2e6d9d8f0f1",  # pragma: allowlist secret
                "code": "time_zone_list",
                "description": "",
                "type": "json",
                "content": [
                    {"name": "New Zealand", "zone": "+12:00"},
                    {"name": "Australia", "zone": "+10:00"},
                    {"name": "South Korea, Japan", "zone": "+09:00"},
                    {"name": "China Mainland, Hong Kong, Macao, Taiwan, Singapore, Philippines, Malaysia", "zone": "+08:00"},
                    {"name": "Thailand, Indonesia, Vietnam", "zone": "+07:00"},
                    {"name": "Kazakhstan, Kyrgyzstan", "zone": "+06:00"},
                    {"name": "Tajikistan, Turkmenistan, Republic of Uzbekistan, India", "zone": "+05:00"},
                    {"name": "United Arab Emirates, Oman, Azerbaijan, Armenia", "zone": "+04:00"},
                    {"name": "Iran", "zone": "+03:30"},
                    {"name": "Belarus,Russian Federation, Kuwait, Saudi Arabia, Turkey", "zone": "+03:00"},
                    {
                        "name": (
                            "Egypt, Estonia, Bulgaria, Finland, Latvia, Lithuania,"
                            "Romania, Moldova, Cyprus, Ukraine, Greece, Israel"
                        ),
                        "zone": "+02:00",
                    },
                    {
                        "name": (
                            "Albania, Ireland, Andorra, Austria, Belgium,"
                            "Bosnia Hercegovina, Poland, Denmark, Germany, France,"
                            "Vatican City State, Netherlands, Czech Republic, Croatia,"
                            "Luxembourg, Malta, Macedonia, Monaco,Norway, Sweden,"
                            "Switzerland, Serbia, San Marino, Slovakia, Slovenia, Spain, Hungary,Italy"
                        ),
                        "zone": "+01:00",
                    },
                    {"name": "Iceland, Portugal, United Kingdom", "zone": "00:00"},
                    {"name": "Argentina, Uruguay", "zone": "-03:00"},
                    {"name": "Dominican Republic", "zone": "-04:00"},
                    {"name": "United States, Brazil, Colombia, Peru", "zone": "-05:00"},
                    {"name": "Mexico", "zone": "-06:00"},
                    {"name": "Mountain Time (US and Canada)", "zone": "-07:00"},
                    {"name": "Canada", "zone": "-08:00"},
                ],
            },
        ]

    elif code in {"yiko_record_enabled", "full_stack_yiko_entry"}:
        data = []

    elif code == "yiko_support_lang":
        data = [
            {
                "resId": "6892ab439937790007c4f2b1",  # pragma: allowlist secret
                "code": "yiko_support_lang",
                "name": "Languages supported by Full Stack YIKO",  # 全栈YIKO支持的语种
                "description": "Languages supported by Full Stack YIKO",  # 全栈YIKO支持的语种
                "type": "json",
                "content": {
                    "lang": [
                        "ar",
                        "de",
                        "en",
                        "fr",
                        "he",
                        "id",
                        "it",
                        "ja",
                        "ko",
                        "pl",
                        "ru",
                        "th",
                        "tr",
                        "vi",
                        "zh_cn",
                        "zh_tw",
                    ],
                },
            },
        ]

    elif code == "webview_trusted_host_suffixes":
        data = [
            {
                "code": "webview_trusted_host_suffixes",
                "name": "Webview trusted host suffixes",
                "description": "Webview trusted host suffixes",
                "type": "json",
                "content": {"suffixes": list(bumper_isc.WEBVIEW_TRUSTED_HOST_SUFFIXES)},
            },
        ]

    elif code == "home_teamwork_entry":
        data = []

    elif code == "goat_h5_url_list":
        pim_url = f"https://{contenturl}/pim"
        goat_url = f"https://{pim_host()}/app_adv/goat"
        data = [
            {
                "resId": "688b1876307bf300077456e8",  # pragma: allowlist secret
                "code": "goat_h5_url_list",
                "name": "Goat network setup H5",
                "description": "URLs of the HTML5 pages used by the Goat setup",
                "type": "json",
                "content": {
                    "set_pin_code_guide": f"{pim_url}/set_pin_code_guide.html?t=set_pin_code_guide",
                    "bt_advanced_features": f"{pim_url}/advanced_features.html?t=advanced_features",
                    "winter_guide": f"{goat_url}/winter_guide.html?_t=winter_guide",
                    "common_set_pin_guide": f"{goat_url}/pin_code_settings.html?_t=pin_code_settings",
                    "rtk_install_method": f"{goat_url}/rtk.html?_t=rtk",
                },
            },
        ]

    elif code == "globalapp_netcfg_h5_url_list":
        base_url = f"https://{pim_host()}/app_adv/pim"
        data = [
            {
                "resId": "642fc135604348000681bfd2",  # pragma: allowlist secret
                "code": "globalapp_netcfg_h5_url_list",
                "name": "globalapp Distribution Network Process H5",
                "description": "globalapp URL of the HTML5 page used in the distribution network process",
                "type": "json",
                "content": {
                    "network_setup": f"{base_url}/network_setup_preparation_by_series.html?t=network",
                    "findqrcodenew": f"{base_url}/find_qrcode.html?t=findqrcodenew",
                    "faqproblem": f"{base_url}/faq_problem_new.html?t=faqproblem",
                    "autofind": f"{base_url}/active_discovery.html?t=autofind",
                    "notFoundAPUrl": f"{base_url}/network_setup_preparation_by_series.html?_t=findDbWifi",
                    "notFoundBTUrl": f"{base_url}/active_discovery.html?t=notFoundBTUrl",
                    "viewWiFi": f"{base_url}/viewWiFi.html?t=viewWiFi",
                },
            },
        ]

    if data is None:
        _LOGGER.error(f"code is not know :: {code}")
        data = []
    return data


@routes.view(f"{PREFIX}/appsvr/service/list")
@bind(LEGACY)
async def _handle_service_list(request: Request) -> Any:
    """Service list.

    Every service of the API is served by the same server, so the answer
    names the service and the domain, without the region of the cloud. The
    broker of the MQTT keeps its name and the broker of the XMPP its port,
    because the router tells them apart.
    """
    area_code = request.query.get("area", bumper_isc.ECOVACS_DEFAULT_COUNTRY).lower()
    return service_list(area_code)


@routes.view(f"{PREFIX}/appsvr/improve")
@bind(LEGACY_BARE)
async def _handle_improve(request: Request) -> Any:
    """Improve."""
    query_did = request.query.get("did", "")
    query_mid = request.query.get("mid", "")
    query_uid = request.query.get("uid", "")
    query_lang = request.query.get("lang", "").lower()
    query_a = request.query.get("a", "")
    query_c = request.query.get("c", "")
    query_v = request.query.get("v", "")
    query_p = request.query.get("p", "")
    query_show_remark = request.query.get("show_remark", "")
    query_token = ""
    query_token_tmp: dict[str, Any] | str = request.query.get("auth", {})
    if isinstance(query_token_tmp, dict):
        query_token = query_token_tmp.get("token", "")

    domain = api_host("adv-app", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)
    content = (
        f"https://{domain}/pim/productImprovePlan_ww.html?initSync=false&did={query_did}"
        f"&mid={query_mid}&uid={query_uid}&lang={query_lang}&a={query_a}&c={query_c}&v={query_v}&"
        f"p={query_p}&id=628dcf819dbd613d9ebb4fe4&ver=11.16&showRemark={query_show_remark}&remark=&token={query_token}"
    )
    return {
        "show": False,
        "content": content,
        "remark": "",
        "updateLog": "",
    }


@routes.view(f"{PREFIX}/appsvr/improve/accept")
async def _handle_improve_accept(_: Request) -> Response:
    """Improve accept."""
    return web.json_response({"code": 0})


@routes.view(f"{PREFIX}/appsvr/improve/user/accept")
async def _handle_improve_user_accept(_: Request) -> Response:
    """Improve accept."""
    return web.json_response({"code": 0, "data": {"accept": False}})


@routes.view(f"{PREFIX}/appsvr/notice/home")
@bind(TODO_RET)
async def _handle_notice_home(_: Request) -> Any:
    """Notice home."""
    return {}


@routes.view(f"{PREFIX}/appsvr/notice/list")
@bind(TODO_RET)
async def _handle_notice_list(_: Request) -> Any:
    """Notice list."""
    return []


@routes.view(f"{PREFIX}/appsvr/ota/firmware")
async def _handle_ota_firmware(_: Request) -> Response:
    """OTA firmware."""
    return web.json_response({"code": -1, "message": "No upgrades at this time"})


@routes.view(f"{PREFIX}/appsvr/device/blacklist/check")
@bind(LEGACY)
async def _handle_device_blacklist_check(_: Request) -> Any:
    """Device blacklist check."""
    return []


@routes.view(f"{PREFIX}/appsvr/product/getConfigGroups")
@bind(LEGACY_BARE.with_side_car("configFAQ", config_faq()))
async def _handle_get_config_groups(_: Request) -> Any:
    """Get config groups."""
    return get_config_groups_response()


@routes.get(f"{PREFIX}/appsvr/codepush/download/{{deployment_key}}")
async def _handle_codepush_download(request: Request) -> Response:
    """Download the CodePush package of a deployment.

    The packages are not part of the distribution, so the answer is 404 until
    one is put in the CodePush directory under the key of its deployment.
    """
    deployment_key = request.match_info.get("deployment_key", "")
    package = file_in_dir(bumper_isc.codepush_dir, deployment_key)
    if package is None:
        _LOGGER.warning(f"No CodePush package for key='{deployment_key}' :: looked in '{bumper_isc.codepush_dir}'")
        return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")

    return web.FileResponse(package)  # type: ignore[return-value]


@routes.view(f"{PREFIX}/appsvr/codepush/checkupdate")
@bind(LEGACY)
async def _handle_codepush_update_check(request: Request) -> Any:
    """CodePush Update check."""
    return codepush_update_check(
        deployment_key=request.query.get("deployment_key", ""),
        label=request.query.get("label", ""),
        package_hash=request.query.get("package_hash", ""),
        package_name=request.query.get("package_name"),
        app_version=request.query.get("app_version", "1.0.0"),
        deployment_name=request.query.get("deployment_name", "Production"),
    )


@routes.get(f"{PREFIX}/appsvr/device/prop/list")
@bind(LEGACY)
async def _handle_device_prop_list(request: Request) -> Any:
    """Device prop list."""
    did = request.query.get("did")
    res = request.query.get("res")
    mid = request.query.get("mid")
    props: list[str] = request.query.get("props", "").split(",")  # OfflineReason,onBattery,onChargeState,...
    ts = utils.get_current_time_as_millis()

    props_result = []
    try:
        async with asyncio.timeout(bumper_isc.HELPER_BOT_TIMEOUT):
            values = await asyncio.gather(*(_ask_robot(prop, did, mid, res) for prop in props))
    except TimeoutError:
        _LOGGER.warning(f"Device prop list ran out of time :: did='{did}' :: props='{props}'")
        values = []

    for prop, value in zip(props, values, strict=False):
        if value is None:
            continue
        props_result.append(
            {
                "key": prop,
                "value": json.dumps({"body": {"data": value}}, separators=(",", ":")),
                "ts": utils.get_millis_to_iso_z(ts),
            },
        )

    return {
        "did": did,
        "ts": ts,
        "props": props_result,
    }


async def _ask_robot(prop: str, did: str | None, mid: str | None, res: str | None) -> Any | None:
    """Ask the robot for a property and return its value.

    A property that does not belong to the robot is not asked for: the API
    answers it itself, with nothing.
    """
    if not prop.startswith("on") or bumper_isc.mqtt_helperbot is None:
        return None

    cmd = f"get{prop[len('on') :]}"
    cmd_json: dict[str, Any] = {
        "cmd": cmd,
        "did": did,
        "mid": mid,
        "res": res,
        "data": {"td": cmd},
    }
    cmd_request = MQTTCommandModel(cmd_json, version=MQTTCommandModel.VERSION_P2P)

    cmd_response = await bumper_isc.mqtt_helperbot.send_command_plain(cmd_request)
    if not isinstance(cmd_response, dict):
        return None
    return cmd_response.get("body", {}).get("data") or None


@routes.view(f"{PREFIX}/appsvr/akvs/start_watch")
async def _handle_akvs_start_watch(request: Request) -> Response:
    """AKVS start watch."""
    utils.default_log_warn_not_impl("_handle_akvs_start_watch")
    query_did = request.query.get("did", "")
    query_auth: str | dict[str, Any] = request.query.get("auth", {})
    query_auth = json.loads(query_auth) if isinstance(query_auth, str) else query_auth
    user_id = query_auth.get("userid", "")
    resource = query_auth.get("resource", "")
    return web.json_response(
        {
            "ret": "ok",
            "region": "eu-central-1",
            "channel": f"production-{query_did}",
            "client_id": f"{user_id}-{resource}",
            "credentials": {
                "AccessKeyId": f"ASIA{secrets.token_hex(10).upper()}",
                "SecretAccessKey": f"wJalrXUtnFEMI/{secrets.token_hex(15)}/{secrets.token_hex(10)}",
                "SessionToken": secrets.token_urlsafe(128),
                "Expiration": "9999-12-31T00:00:00.000Z",
                "TtlSec": 3600,
            },
            "session": f"de/{secrets.token_hex(4)}",
            "ts": utils.get_current_time_as_millis(),
        },
    )


@routes.view(f"{PREFIX}/appsvr/device/{{did}}/nickname")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_device_nickname(request: Request) -> Any:
    """Rename a device."""
    did = request.match_info.get("did", "")
    body = await read_body(request)
    nickname = str(body.get("nickname", "")).strip()
    if not did or not nickname:
        _LOGGER.warning("No did or nickname in the request")
        return None
    if bot_repo.get(did) is None:
        _LOGGER.warning(f"No bot found for {did} (nickname)")
        return None
    bot_repo.set_nick(did, nickname)
    return None


async def _get_global_device_list(request: Request, post_body: Mapping[str, Any]) -> Any:
    """Return the devices of the account."""
    return device_list(_request_user(request, post_body))


def _request_user(request: Request, post_body: Mapping[str, Any]) -> BumperUser | None:
    """Return the account a legacy request names."""
    auth = post_body.get("auth")
    user_id = post_body.get("userId") or post_body.get("userid")
    if not user_id and isinstance(auth, Mapping):
        user_id = auth.get("userid")
    if not user_id:
        user_id = claimed_userid(request)
    if isinstance(user_id, str) and user_id:
        return identity.resolve_user(user_id, prefer_device=True)
    return None


async def _get_codepush(_: Request, __: Mapping[str, Any]) -> Any:
    """Return the CodePush configuration."""
    return {
        "extend": {},
        "type": "microsoft",
        "url": "",
    }


async def _robot_control(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Send a command to the robot and return its answer."""
    data_ctl: Any | None = post_body.get("data", {})
    if not isinstance(data_ctl, dict):
        msg = "Error request, the data of the command is missing"
        raise ApiError(msg=msg, code=2004)
    data_ctl = data_ctl.get("ctl", None)
    if not isinstance(data_ctl, dict):
        msg = "Error request, the command is missing"
        raise ApiError(msg=msg, code=2004)

    cmd = next(iter(data_ctl.keys()))
    cmd_json: dict[str, Any] = data_ctl.get(cmd, {})
    cmd_request = MQTTCommandModel(cmd_json, version=MQTTCommandModel.VERSION_P2P)
    if bumper_isc.mqtt_helperbot is None:
        msg = "Error request, the helper bot is not connected"
        raise ApiError(msg=msg, code=2004)
    return await bumper_isc.mqtt_helperbot.send_command(cmd_request)


async def _get_app_video_url(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Return the urls of the videos of the app."""
    keys: Any = post_body.get("keys", [])
    if not isinstance(keys, list):
        msg = "Error request, the keys of the videos are missing"
        raise ApiError(msg=msg, code=2004)
    data = {}
    for key in keys:
        if key == "t9_promotional_video":
            data[key] = f"https://{bumper_isc.DOMAIN_ALIYUN}/public/t9_promotional_video.mp4"
    return data


async def _get_device_protocol(_: Request, __: Mapping[str, Any]) -> Any:
    """Return the versions of the protocol of the app."""
    return {
        "video": {
            "version": "13.01",
            "hasNewProtocol": False,
            "hasReadOld": True,
            "isAccept": True,
            "protocolUrl": (
                f"https://{pim_host()}/api/pim/protocol.html?version=13.01&lang=en&defaultLang=en&country=DE&type=video"
            ),
        },
        "improve": {
            "version": "11.15",
            "hasNewProtocol": False,
            "hasReadOld": True,
            "isAccept": False,
            "protocolUrl": (
                f"https://{pim_host()}/api/pim/protocol.html?version=11.15&lang=en&defaultLang=en&country=DE&type=improve"
            ),
        },
    }


async def _decode_qr_code(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Return the product of the robot the qr code belongs to."""
    qrcode = post_body.get("qrcode", "")
    if not isinstance(qrcode, str):
        return {}

    qrcode_q = parse_qs(urlparse(qrcode).query)
    sn = qrcode_q.get("sn", [None])[0]
    mid = qrcode_q.get("mid", [None])[0]
    if not isinstance(sn, str) and not isinstance(mid, str):
        return {}

    robot = None
    product_category = None
    for botprod in get_product_iot_map():
        if botprod["classid"] != mid:
            continue
        name = botprod.get("product", {}).get("name")
        robot = get_config_groups_robot(value=name, key="groupName")
        product_category = get_product_category(device_name=name, robot=robot)
        if robot:
            robot["mid"] = mid
            robot["customSteps"] = robot.pop("cusSteps")
            robot["name"] = robot.pop("groupName")
            robot.pop("groupId")
            robot.pop("service")
            robot.pop("products")
            robot.pop("smartTypes")
            robot.pop("icon")
            robot.pop("sort")
        break

    return {
        "supportApp": "global",
        "belongApp": ["ecoglobal", "yeedi"],
        "supportRegion": "International",
        "qrType": "config",
        "productCategory": product_category,
        "code_sn": sn,
        "configGuide": robot,
        "configFAQ": config_faq(),
    }


# ----------- Mapping -----------
APP_DO_OPERATIONS.update(
    {
        "GetGlobalDeviceList": Operation(TODO_RET.with_data_key("devices"), _get_global_device_list),
        "GetCodepush": Operation(TODO_RET, _get_codepush),
        "RobotControl": Operation(TODO_RET, _robot_control),
        "GetAppVideoUrl": Operation(TODO_RET, _get_app_video_url),
        "GetDeviceProtocolV2": Operation(TODO_RET, _get_device_protocol),
        "DecodeQrCode": Operation(TODO_RET, _decode_qr_code),
    },
)
