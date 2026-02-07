"""Appsvr plugin module."""

from collections.abc import Iterable, Mapping
import copy
import json
import logging
import secrets
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import MQTTCommandModel
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_service
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_code_push_config, get_config_groups_response, get_product_config_batch, get_product_iot_map
from bumper.web.utils.models import VacBotDevice
from bumper.web.utils.response_helper import response_error_v5, response_success_v2, response_success_v3, response_success_v4

_LOGGER = logging.getLogger(__name__)


class AppsvrPlugin(WebserverPlugin):
    """Appsvr plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/appsvr/app.do", _handle_app_do),
            web.route("*", "/appsvr/app/config", _handle_app_config),
            web.route("*", "/appsvr/improve", _handle_improve),
            web.route("*", "/appsvr/improve/accept", _handle_improve_accept),
            web.route("*", "/appsvr/improve/user/accept", _handle_improve_user_accept),
            web.route("*", "/appsvr/notice/home", _handle_notice_home),
            web.route("*", "/appsvr/notice/list", _handle_notice_list),
            web.route("*", "/appsvr/oauth_callback", auth_service.oauth_callback),
            web.route("*", "/appsvr/oauth/token", auth_service.oauth_callback),  # TODO: implement
            web.route("*", "/appsvr/service/list", _handle_service_list),
            web.route("*", "/appsvr/ota/firmware", _handle_ota_firmware),
            web.route("*", "/appsvr/device/blacklist/check", _handle_device_blacklist_check),
            web.route("*", "/appsvr/akvs/start_watch", _handle_akvs_start_watch),
            # web.route("*", "/appsvr/akvs/end_watch", _handle_akvs_end_watch), # TODO: implement
            web.route("*", "/appsvr/product/getConfigGroups", _handle_get_config_groups),
        ]


async def _handle_app_do(request: Request) -> Response:
    """App do."""
    try:
        post_body: Mapping[str, Any]
        if request.content_type == "application/x-www-form-urlencoded":
            post_body = await request.post()
        else:
            post_body = json.loads(await request.text())

        todo = post_body.get("todo", "")

        if todo == "GetGlobalDeviceList":
            return response_success_v2(data=create_device_list(), data_key="devices")

        if todo == "GetCodepush":
            return response_success_v2(
                data={
                    "extend": {},
                    "type": "microsoft",
                    "url": "",
                },
            )

        if todo == "RobotControl":
            data_ctl: Any | None = post_body.get("data", {})
            if not isinstance(data_ctl, dict):
                return response_error_v5()
            data_ctl = data_ctl.get("ctl", None)
            if not isinstance(data_ctl, dict):
                return response_error_v5()

            cmd = next(iter(data_ctl.keys()))
            cmd_json: dict[str, Any] = data_ctl.get(cmd, {})
            cmd_request = MQTTCommandModel(cmd_json, version=MQTTCommandModel.VERSION_P2P)
            if bumper_isc.mqtt_helperbot is not None:
                return await bumper_isc.mqtt_helperbot.send_command(cmd_request)

        if todo == "GetAppVideoUrl":
            keys: Any = post_body.get("keys", [])
            if not isinstance(keys, list):
                return response_error_v5()
            data = {}
            for key in keys:
                if key == "t9_promotional_video":
                    data[key] = f"https://{bumper_isc.DOMAIN_ALI}/public/t9_promotional_video.mp4"
            return response_success_v2(data=data)

        if todo == "GetDeviceProtocolV2":
            return response_success_v2(
                data={
                    "video": {
                        "version": "13.01",
                        "hasNewProtocol": False,
                        "hasReadOld": True,
                        "isAccept": True,
                        "protocolUrl": (
                            f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/protocol.html?version=13.01"
                            "&lang=en&defaultLang=en&country=DE&type=video"
                        ),
                    },
                    "improve": {
                        "version": "11.15",
                        "hasNewProtocol": False,
                        "hasReadOld": True,
                        "isAccept": False,
                        "protocolUrl": (
                            f"https://{bumper_isc.DOM_SUB_PORT}/api/pim/protocol.html?version=11.15"
                            "&lang=en&defaultLang=en&country=DE&type=improve"
                        ),
                    },
                },
            )

        # if todo =="DecodeQrCode": # TODO: implement (add bot per qrcode)

        _LOGGER.warning(f"todo is not know :: {todo!s}")
        return response_error_v5()
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_app_config(request: Request) -> Response:
    """App config."""
    code = request.query.get("code", "")
    data: list[dict[str, Any]] | None = None
    # configurl = f"codepush-base.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
    # backupurl = f"codepush-base.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
    contenturl = f"adv-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"

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
                "resId": "675681bca7c061000750cb05",
                "code": "yiko_support_lang",
                "name": "Languages supported by Full Stack YIKO",  # 全栈YIKO支持的语种
                "description": "Languages supported by Full Stack YIKO",  # 全栈YIKO支持的语种
                "type": "json",
                "content": {"lang": ["en"]},
            },
        ]

    # elif code == "globalapp_netcfg_h5_url_list":  # TODO: implement (add bot per qrcode)

    if data is None:
        _LOGGER.error(f"code is not know :: {code}")
        data = []
    return response_success_v3(data=data)


async def _handle_service_list(request: Request) -> Response:
    """Service list."""
    try:
        area_code = request.query.get("area", bumper_isc.ECOVACS_DEFAULT_COUNTRY).lower()
        dc_code = utils.get_dc_code(area_code)
        sub_domain_1 = f"{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
        sub_domain_2 = f"{bumper_isc.DOM_SUB_2}{bumper_isc.DOMAIN_MAIN}"
        sub_domain_3 = f"{bumper_isc.DOM_SUB_3}{bumper_isc.DOMAIN_MAIN}"

        data = {
            "account": f"users-base.{sub_domain_1}",
            "adv": f"adv-app.{sub_domain_1}",
            "dc": dc_code,
            "jmq": f"jmq-ngiot-eu.{sub_domain_2}",
            "lb": f"lbo.{bumper_isc.DOMAIN_MAIN}",
            "magw": f"api-app.{sub_domain_1}",
            "msgcloud": f"msg-eu.{bumper_isc.DOMAIN_MAIN}:5223",
            "ngiot": f"api-ngiot.{sub_domain_1}",
            "ngiotLb": f"jmq-ngiot-de.{sub_domain_3}",
            "nlp": f"iot-api-nlp.{sub_domain_1}",
            "rop": f"api-rop.{sub_domain_1}",
            "bigdata": f"bigdata-europe.{bumper_isc.DOMAIN_MAIN}",
            "base": f"api-base.{sub_domain_1}",
            "eis": f"eis-nlp.{sub_domain_1}",
            "codepush": f"codepush-base.{sub_domain_1}",
            "setApConfig": {
                "a": area_code,
                "r": bumper_isc.DOMAIN_MAIN,
                "v": "ww",
            },
        }

        return response_success_v2(data=data)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_improve(request: Request) -> Response:
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

    domain = f"adv-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
    content = (
        f"https://{domain}/pim/productImprovePlan_ww.html?initSync=false&did={query_did}"
        f"&mid={query_mid}&uid={query_uid}&lang={query_lang}&a={query_a}&c={query_c}&v={query_v}&"
        f"p={query_p}&id=628dcf819dbd613d9ebb4fe4&ver=11.16&showRemark={query_show_remark}&remark=&token={query_token}"
    )
    return response_success_v4(
        {
            "show": False,
            "content": content,
            "remark": "",
            "updateLog": "",
        },
    )


async def _handle_improve_accept(_: Request) -> Response:
    """Improve accept."""
    return web.json_response({"code": 0})


async def _handle_improve_user_accept(_: Request) -> Response:
    """Improve accept."""
    return web.json_response({"code": 0, "data": {"accept": False}})


async def _handle_notice_home(_: Request) -> Response:
    """Notice home."""
    return response_success_v2(data={})


async def _handle_notice_list(_: Request) -> Response:
    """Notice list."""
    return response_success_v2(data={})


async def _handle_ota_firmware(_: Request) -> Response:
    """OTA firmware."""
    return web.json_response({"code": -1, "message": "No upgrades at this time"})


async def _handle_device_blacklist_check(_: Request) -> Response:
    """Device blacklist check."""
    return response_success_v3(data=[])


def create_device_list() -> list[dict[str, Any]]:
    """Create bot device list."""
    return [
        device
        for bot in bot_repo.list_all()
        if bot.class_id and bot.class_id != "" and (device := _include_product_iot_map_info(bot)) is not None
    ]


def _include_product_iot_map_info(bot: VacBotDevice) -> dict[str, Any] | None:
    for botprod in get_product_iot_map():
        if botprod["classid"] != bot.class_id:
            continue

        result: dict[str, Any] = copy.deepcopy(bot.as_dict())
        result.pop("mqtt_connection")
        result.pop("xmpp_connection")

        if (botprod_invent := botprod.get("product")) is not None:
            result["pid"] = botprod_invent["_id"]
            result["materialNo"] = botprod_invent["materialNo"]
            result["deviceName"] = botprod_invent["name"]
            result["model"] = botprod_invent["model"]
            result["UILogicId"] = botprod_invent["UILogicId"]
            result["ota"] = botprod_invent["ota"]
            result["icon"] = botprod_invent["iconUrl"]
            result["product_category"] = "DEEBOT" if botprod_invent["name"].startswith("DEEBOT") else "UNKNOWN"

        result["status"] = 1 if bot.mqtt_connection or bot.xmpp_connection else 0

        result["otaUpgrade"] = {}
        result["updateInfo"] = {"changeLog": "", "needUpdate": False}
        result["shareable"] = bool(bot.mqtt_connection)
        result["sharedDevice"] = False

        # TODO: improve as non static
        result["homeId"] = bumper_isc.HOME_ID
        result["homeSort"] = 1

        if bot.mqtt_connection:
            result["bindTs"] = utils.get_current_time_as_millis()
            result["offmap"] = True

            product_config_batch: list[dict[str, Any]] = get_product_config_batch()

            result["scode"] = {
                "tmallstand": False,
                "video": False,
                "battery": True,
                "clean": True,
                "charge": True,
                "chargestate": True,
            }
            for product_config in product_config_batch:
                if botprod_invent and botprod_invent["_id"] == product_config.get("pid", ""):
                    result["scode"] = {
                        "tmallstand": product_config.get("tmallstand", False),
                        "video": product_config.get("video", False),
                        "battery": product_config.get("battery", True),
                        "clean": product_config.get("clean", True),
                        "charge": product_config.get("charge", True),
                        "chargestate": product_config.get("", True),
                    }
                    break

            result["service"] = {
                "jmq": f"jmq-ngiot-eu.{bumper_isc.DOM_SUB_2}{bumper_isc.DOMAIN_MAIN}",
                "mqs": f"api-ngiot.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}",
            }

        return result
    return None


async def _handle_akvs_start_watch(request: Request) -> Response:
    """AKVS start watch."""
    # TODO: check what's needed to be implemented
    # 8.219.176.88 sgp-sdk.openaccount.aliyun.com
    # a2JaaxoKXLq.iot-as-mqtt.cn-shanghai.aliyuncs.com
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


async def _handle_get_config_groups(_: Request) -> Response:
    """Get config groups."""
    try:
        return response_success_v3(
            code=0,
            msg_key="msg",
            msg="success",
            result_key="configFAQ",
            result={
                "wifiFAQUrl": "https://portal-ww.ecouser.net/api/pim/faqproblem.html?lang=en&defaultLang=en",
                "notFoundAPUrl": "https://portal-ww.ecouser.net/api/pim/findDbWifi.html?lang=en&defaultLang=en",
                "configFailedUrl": "https://portal-ww.ecouser.net/api/pim/configfail.html?lang=en&defaultLang=en",
            },
            data_key="data",
            data=get_config_groups_response(),
        )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError
