"""Appsvr plugin module."""

from collections.abc import Iterable, Mapping
import copy
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import db, utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_util
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_error_v5, response_success_v3, response_success_v4, response_success_v5

from .pim import get_product_iot_map

_LOGGER = logging.getLogger(__name__)


class AppsvrPlugin(WebserverPlugin):
    """Appsvr plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "POST",
                "/appsvr/app.do",
                _handle_app_do,
            ),
            web.route(
                "*",
                "/appsvr/app/config",
                _handle_app_config,
            ),
            web.route(
                "*",
                "/appsvr/improve",
                _handle_improve,
            ),
            web.route(
                "*",
                "/appsvr/improve/accept",
                _handle_improve_accept,
            ),
            web.route(
                "*",
                "/appsvr/notice/home",
                _handle_notice_home,
            ),
            web.route(
                "*",
                "/appsvr/oauth_callback",
                _handle_oauth_callback,
            ),
            web.route(
                "*",
                "/appsvr/service/list",
                _handle_service_list,
            ),
            web.route(
                "*",
                "/appsvr/ota/firmware",
                _handle_ota_firmware,
            ),
            web.route(
                "*",
                "/appsvr/device/blacklist/check",
                _handle_device_blacklist_check,
            ),
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
            bots = db.bot_get_all()
            devices: list[dict[str, Any]] = []
            for bot in bots:
                if bot.get("class", "") != "":
                    device = _include_product_iot_map_info(bot)
                    # Happens if the bot isn't on the EcoVacs Home list
                    if device is not None:
                        devices.append(device)
            return response_success_v4(devices, data_key="devices")

        if todo == "GetCodepush":
            return response_success_v4(
                {
                    "extend": {},
                    "type": "microsoft",
                    "url": "",
                },
            )

        if todo == "RobotControl":
            # TODO: check what's needed to be implemented
            utils.default_log_warn_not_impl("_handle_app_do/RobotControl")
            # EXAMPLE request:
            #     {
            #         "app": {
            #             "id": "ecovacs",
            #             "signature": "SIG",
            #             "ts": 1697936046117
            #         },
            #         "auth": {
            #             "realm": "ecouser.net",
            #             "resource": "GLB521a51aG0",
            #             "token": "...",
            #             "userid": "ID",
            #             "with": "users"
            #         },
            #         "data": {
            #             "ctl": {
            #                 "GetBatteryInfo": {
            #                     "all": false,
            #                     "cmd": "GetBatteryInfo",
            #                     "did": "DID",
            #                     "mid": "p95mgv",
            #                     "res": "Gy2C",
            #                     "type": "p2p"
            #                 }
            #             }
            #         },
            #         "did": "DID",
            #         "mid": "p95mgv",
            #         "res": "Gy2C",
            #         "todo": "RobotControl"
            #     }
            #
            # EXAMPLE response:
            #     {
            #         "code": 0,
            #         "data": {
            #             "GetBatteryInfo": {
            #                 "did": "DID",
            #                 "power": 100,
            #                 "ret": "ok"
            #             }
            #         },
            #         "ret": "ok",
            #         "todo": "result"
            #     }
            return response_success_v4({})

        if todo == "GetAppVideoUrl":
            keys = post_body.get("keys", [])
            data = {}
            for key in keys:
                if key == "t9_promotional_video":
                    data[key] = "https://globalapp-eu.oss-eu-central-1.aliyuncs.com/public/t9_promotional_video.mp4"
            return response_success_v4(data)

        _LOGGER.error(f"todo is not know :: {todo}")
        return response_error_v5()
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_app_config(request: Request) -> Response:
    """App config."""
    code = request.query.get("code", "")
    data: list[dict[str, Any]] = []

    if code == "app_lang_enum":
        data = [
            {
                "code": "app_lang_enum",
                "description": "",
                "name": "APP Language Enumeration Lists",
                "resId": "622ee4977404d4518fd575fb",
                "type": "json",
                "content": {
                    "ar": "العربية",
                    "cs": "český",
                    "da": "Dansk",
                    "de": "Deutsch",
                    "en": "English",
                    "en-au": "English(Australian)",
                    "en-ca": "English(Canadian)",
                    "en-gb": "English(United Kingdom)",
                    "en-in": "English(Indian)",
                    "en-us": "English(American)",
                    "es": "Español",
                    "et": "Eesti",
                    "fa": "فارسی",
                    "fr": "Français",
                    "he": "עברי",
                    "hk": "粤語",
                    "hu": "Magyar",
                    "id": "Indonesia",
                    "it": "Italiano",
                    "ja": "日本語",
                    "ko": "한국어",
                    "lt": "Lietuvos",
                    "lv": "Latvijas",
                    "my": "Malay",
                    "nl": "Nederlands",
                    "no": "Norsk språk",
                    "pl": "Polski",
                    "pt": "Português",
                    "ru": "Pусский",
                    "sk": "Slovenský jazyk",
                    "sv": "Svenska",
                    "th": "ไทย",
                    "tw": "國語",
                    "vn": "Tiếng Việt",
                    "zh": "普通话",
                    "zh-hans": "简体中文",
                    "zh-hant": "繁體中文",
                    "zh_cn": "简体中文",
                },
            },
        ]

    elif code == "codepush_config":
        sub_domain_suffix_1 = ""  # .cn
        sub_domain_suffix_2 = ""  # .dc-cn

        data = [
            {
                "code": "codepush_config",
                "description": "",
                "name": "global codepush",
                "resId": "614d73873d80d1deed8be299",
                "type": "json",
                "content": {
                    "andyproH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "SmTGB14wfXJnTZ0iHh03tEq83S9j6vK_B0zI9s",
                            "staging": "zhiPemGhbl0FV3V8_kBY9luOBgLd55YwYuImG",
                        },
                        "version": "1.0.0",
                    },
                    "andyprocq": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "4BNGgbVnlX72LzmReCJ6Wk8kip7-r7Ryzvq3ML",
                            "staging": "Q-nsZ6qHNNen-Dse_2r6XlxW0bHhDu-ZaV-0H",
                        },
                        "version": "1.0.0",
                    },
                    "at90": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "1W2Lw4KvqTz0D-UMxzfZSEcv2yWpoD7SZyGzb4",
                            "staging": "bokwAmqkL-svCnwI8Fd1pGSHBSf-aBoXWtNyi",
                        },
                        "version": "1.0.0",
                    },
                    "at91": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "DWfSnnORMkobKsaS3V0e7VMGVwSiHZqEvtEsJA",
                            "staging": "XVbaPU2hBbzAWC4FvpLR_Jr14pTYdZqQQYzj-",
                        },
                        "version": "1.0.0",
                    },
                    "at92": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "gkhxiPWw5-v7UPEj0ImuPLMBME57DqrNmMHdtt",
                            "staging": "XutZcQwGKVM2bXjxa-xej1bTkKn7DbZuNGav-",
                        },
                        "version": "1.0.0",
                    },
                    "avacq": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "GxNUohEV_hHSw6Gap-StWiW9gTnP32-QIgkoVb",
                            "staging": "5FfFTL-ZIKF2ixpcX_E5Sua8Ixqn55Mpg6W_q",
                        },
                        "version": "1.0.0",
                    },
                    "beluga": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "production": "vhaH5f2nNpKiXPFDhVq6yf4gr6xFGAOKoMGTFT",
                            "staging": "RT1aLYD7YwQms9vs539Qn5GjRlExVWeMTOHeF",
                        },
                        "version": "1.0.0",
                    },
                    "bluetooth_detect": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "ZZ4sMVW8D4aLSFq5-2sBop1cEdAGDgTzcC5WDU",
                            "staging": "L1wUtnf9yb52PDqldFJiHkV9AXphuh4814NA-",
                        },
                        "version": "1.0.0",
                    },
                    "bruce3DH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "hNnGhKA8jkPLQfmT9VVLWJMvssRIADF3s65tfD",
                            "staging": "iAz1OvOFinTA6DcotZL4hVFK9P1-9gEc63Syb",
                        },
                        "version": "1.0.0",
                    },
                    "bruce3dRes": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "uOtNaTLAbWAFiQhovEqW4nyhvUbSxFNF92vdiV",
                            "staging": "4mm6F3Jak4JtMwO2AMHlbTHElUOMWZd_IzL5P",
                        },
                        "version": "2.1.4",
                    },
                    "bruceMore": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "P5sN80W6TdO5nQ63CJWvtTgnu-BKYqxQmf8IEi",
                            "staging": "1FXFufgsGXUcHc2F7eLWPPDXDsVySG9sj5VKc",
                        },
                        "version": "1.0.0",
                    },
                    "common_h5_wificonfig": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "5qjDOMa4u1euqWEwqEZD6jimbrAemeiaRV_CZ7",
                            "staging": "QHW58TtxPsWGjmZ50kNxAA0HTyS_Z-SB0Arr1",
                        },
                        "version": "1.0.0",
                    },
                    "feedback": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "WItFnpEfp-Rbc2B9hfLeuinBr03GZ-JhH2T4HO",
                            "staging": "C_PwRTI0NRVP9F3OBxYXRC8UvLrneiXnsvztE",
                        },
                        "version": "1.0.0",
                    },
                    "furniture": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "VKfJlwYCG58sJN3FfCjYGqRd2M81HCIn2kOBrw",
                            "staging": "M7lyba6OXxVBG_KrkIgbv569Jnwz6V1gdk0oA",
                        },
                        "version": "1.0.0",
                    },
                    "goat": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "M2oNdmHoQQT57oQ8BmfUQJtEirFCtm9eJVxZm2",
                            "staging": "Yb_c8B9JHVqY_WLajIurkKaUTG4TGVkLyXYj-",
                        },
                        "version": "1.0.0",
                    },
                    "goatWifiConfig": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "vsSrYLDXjkI7QPGkF3YghqQRoioIkQLtg2jn6Q",
                            "staging": "nhcEIBlRsXGOHySHFtHnNirZl4Nm4ZvgJGk9C",
                        },
                        "version": "1.0.0",
                    },
                    "hwPush": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "4cPMrbntK2vbs-KRgsrJq4HI0W-hrTHP1BMTKq",
                            "staging": "dXgPCPco60Fc_JlZ5S_bS0ZanhlaNiU9elFaj",
                        },
                        "version": "1.0.0",
                    },
                    "language": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "mQ7b_ImAD5t_hapi17Dt_CK0ZU1nArKrTYdCTI",
                            "staging": "IPbEkwK4wD9MCzWtncXQ8C0lDdLQxOMn13Owg",
                        },
                        "version": "1.0.0",
                    },
                    "n10H5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "XvkGE1ck0ryXYrKiZfLkey8rLaGQrdJrK6NbhT",
                            "staging": "P7Tc7dKMMw_2rsNYnjL8avKNGBvZwFGgWXc3S",
                        },
                        "version": "1.0.0",
                    },
                    "netDiagno": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "1YhT34XSJJ-iUPtrBsi-zXA1LPCyAtLjsEW7IU",
                            "staging": "Cqn5Kl-UYcru2RYKN9xJvMHaA7lWAmd7d-vli",
                        },
                        "version": "1.0.0",
                    },
                    "robotDiscovery": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "z94xCOc2FnBqdw6IJMFvMoWFLALxVNGsK0wHuJ",
                            "staging": "w3nVjj2mBV1JdO8tBO2JcU8EL4W6nBrv8KOVo",
                        },
                        "version": "1.0.0",
                    },
                    "t103DH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "0XLlHQNfNd0YUpiD-gDe1h6oIctlsVKwpcmViH",
                            "staging": "9ShOioxbphO8yAj2eCH9dxdokNkey5fUESL1O",
                        },
                        "version": "1.0.0",
                    },
                    "t10H5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "mackERM5dTh8cqiAk9MEBuRhdgLEytf1emmE4H",
                            "staging": "f93aQ5QrspoyG5vYvPTICrfmS65YJVNFuNJ0o",
                        },
                        "version": "1.0.0",
                    },
                    "t10More": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "RSYAx668chaf0tpKvf1kJNaVJmDzi4g83wsg78",
                            "staging": "yQeevYX5q1yVhr_dH0VwKNJ3x3iDBSxJ-E91G",
                        },
                        "version": "1.0.0",
                    },
                    "t30h5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "FKk06D18kgJF89hmXCNYM9QOr3_XhCQ57H2S_G",
                            "staging": "KyAMEVANA1hGBFwc53QPpHN3dy7Atxp51jW93",
                        },
                        "version": "1.0.0",
                    },
                    "t93DH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "SfL1sY_6V3jXpve1cm0P1NbWqdDBoGlhCAfs0j",
                            "staging": "IVlc9Cp2zblCoF06DpPONjEud0I1I1WgKVF9L",
                        },
                        "version": "1.0.0",
                    },
                    "t9aivi3DH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "xfpg077WmAycqI0avmPp2CEneEbPudBW-cIdOO",
                            "staging": "WSXU46W-20J2FJYW9cp46zglU7ou9-vGOQpP1",
                        },
                        "version": "1.0.0",
                    },
                    "test20": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "n1MBCZHFWVi3PFdxg-u6N7yF6CStEXtlKms3O",
                            "staging": "vCmfAvE-g-OkOvLm8ckIfjLwf1c9a-fBGI6u2",
                        },
                        "version": "1.0.0",
                    },
                    "w2": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "bjPgGQImxLfkkwaGfJSdiOQJjqY8zePT0Zn3EE",
                            "staging": "IVU5ksl1Pg6LCxY6E_0Z7y4gZlSiR8N-skdXT",
                        },
                        "version": "1.0.0",
                    },
                    "winbot": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "QEdpHlrNp1ANHhYFbEJ63dYo1bcsZCShQ9H938",
                            "staging": "uYmbjPDsvnfIBjjY9pM0PdESrZX8_QxMpm-bH",
                        },
                        "version": "1.0.0",
                    },
                    "x1proH5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "Wt3wZa8Hs69dbZgtNXsiNVcda9P-GBSBDm4lDw",
                            "staging": "UvSn3tgPRYfmhwT7YOwP4WO5Us6HKC-sq91HS",
                        },
                        "version": "1.0.0",
                    },
                    "x2omnih5": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "aDSKvlow04p5n8c-E3VyqMFu4uUqtGHPl9QPdW",
                            "staging": "xScQMVfxtwE-2zxua1W5ErV5VcDIRV2dNftu3",
                        },
                        "version": "1.0.0",
                    },
                    "y30h5": {
                        "deploymentKey": {
                            "current": "production",
                            "production": "26p8nXPBq_eugaHR-cVBFil_ef7YYiVE68PjbT",
                            "staging": "MM16kaUHzbh_ptTsN1Fb35A_B86JHtlRNQwgD",
                        },
                        "version": "1.0.0",
                    },
                    "z2h5": {
                        "backupurl": f"codepush-base{sub_domain_suffix_2}{sub_domain_suffix_1}.ecouser.net",
                        "deploymentKey": {
                            "current": "production",
                            "production": "PYBJrRsobI0I0daHnkZ-NQ5Y0p8CdmXEBeFlgJ",
                            "staging": "JOh7dYs9kfQmfKDt7efqjnvvqWGsoyQeshDOS",
                        },
                        "version": "1.0.0",
                    },
                },
            },
        ]

    elif code == "base_station_guide":
        domain = "https://adv-app.dc-cn.cn.ecouser.net"
        data = [
            {
                "code": "base_station_guide",
                "content": f"{domain}/pim/base_station_guide_newton_curi.html?lang=en&defaultLang=en",
                "description": "",
                "name": "Introduction to AES base stations",
                "resId": "61cd0abe312d7cfc89acf608",
                "type": "text",
            },
        ]

    elif code == "time_zone_list":
        zone_name_01 = "Egypt, Estonia, Bulgaria, Finland, Latvia, Lithuania, Romania, Moldova, Cyprus, Ukraine, Greece, Israel"
        zone_name_02 = (
            "Albania, Ireland, Andorra, Austria,Belgium, Bosnia Hercegovina, Poland, Denmark,"
            " Germany, France, Vatican City State, Netherlands, Czech Republic, Croatia, Luxembourg,"
            " Malta, Macedonia, Monaco,Norway, Sweden, Switzerland, Serbia, San Marino, Slovakia, Slovenia, Spain, Hungary,Italy"
        )
        data = [
            {
                "code": "time_zone_list",
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
                    {"name": zone_name_01, "zone": "+02:00"},
                    {"name": zone_name_02, "zone": "+01:00"},
                    {"name": "Iceland, Portugal, United Kingdom", "zone": "00:00"},
                    {"name": "Argentina, Uruguay", "zone": "-03:00"},
                    {"name": "Dominican Republic", "zone": "-04:00"},
                    {"name": "United States, Brazil, Colombia, Peru", "zone": "-05:00"},
                    {"name": "Mexico", "zone": "-06:00"},
                    {"name": "Mountain Time (US and Canada)", "zone": "-07:00"},
                    {"name": "Canada", "zone": "-08:00"},
                ],
                "description": "",
                "resId": "61a055be6533d2e6d9d8f0f1",
                "type": "json",
            },
        ]

    # TODO: yiko_record_enabled
    # elif code == "yiko_record_enabled":
    #     data = [
    #         {
    #             "code": "yiko_record_enabled",
    #             "content": {
    #                 "enabled": False,
    #                 "url": "",
    #             },
    #             "description": "",
    #             "name": "YIKO recording function switch",
    #             "resId": "61a055be6533d2e6d9d8f0f1",
    #             "type": "json",
    #         },
    #     ]

    if len(data) <= 0:
        _LOGGER.error(f"code is not know :: {code}")
    return response_success_v3(data)


async def _handle_service_list(request: Request) -> Response:
    """Service list."""
    try:
        area_code = request.query.get("area", bumper_isc.ECOVACS_DEFAULT_COUNTRY).lower()
        dc_code = utils.get_dc_code(area_code)

        # NOTE: original urls comment out as they are sub sub domain,
        # which the current certificate is not valid
        # using url, where the certs is valid
        sub_domain_suffix_1 = ""  # .dc-eu
        sub_domain_suffix_2 = ""  # .dc-as
        sub_domain_suffix_3 = ""  # .area
        sub_domain_suffix_4 = ""  # .dc
        sub_domain_suffix_ww = ""  # .ww

        data = {
            "account": f"users-base{sub_domain_suffix_1}{sub_domain_suffix_ww}.ecouser.net",
            "adv": f"adv-app{sub_domain_suffix_1}{sub_domain_suffix_ww}.ecouser.net",
            "dc": dc_code,
            "jmq": f"jmq-ngiot-eu{sub_domain_suffix_4}{sub_domain_suffix_ww}.ecouser.net",
            "lb": "lbo.ecouser.net",
            "magw": f"api-app{sub_domain_suffix_1}{sub_domain_suffix_ww}.ecouser.net",
            "msgcloud": "msg-eu.ecouser.net:5223",
            "ngiot": f"api-ngiot{sub_domain_suffix_1}{sub_domain_suffix_ww}.ecouser.net",
            "ngiotLb": f"jmq-ngiot-de{sub_domain_suffix_3}{sub_domain_suffix_ww}.ecouser.net",
            "nlp": f"iot-api-nlp{sub_domain_suffix_2}{sub_domain_suffix_ww}.ecouser.net",
            "rop": f"api-rop{sub_domain_suffix_1}{sub_domain_suffix_ww}.ecouser.net",
            "setApConfig": {
                "a": area_code,
                "r": "ecouser.net",
                "v": "ww",
            },
        }

        return response_success_v4(data)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_oauth_callback(request: Request) -> Response:
    """Oauth callback."""
    return auth_util.oauth_callback(request)


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

    # https://adv-app.dc-eu.ww.ecouser.net
    content = (
        f"https://adv-app.ecouser.net/pim/productImprovePlan_ww.html?initSync=false&did={query_did}"
        f"&mid={query_mid}&uid={query_uid}&lang={query_lang}&a={query_a}&c={query_c}&v={query_v}&"
        f"p={query_p}&id=628dcf819dbd613d9ebb4fe4&ver=11.16&showRemark={query_show_remark}&remark=&token={query_token}"
    )
    return response_success_v5(
        {
            "content": content,
            "remark": "",
            "show": False,
        },
    )


async def _handle_improve_accept(_: Request) -> Response:
    """Improve accept."""
    return web.json_response({"code": 0})


async def _handle_notice_home(_: Request) -> Response:
    """Notice home."""
    return response_success_v4({})


async def _handle_ota_firmware(_: Request) -> Response:
    """OTA firmware."""
    return web.json_response({"code": -1, "message": "No upgrades at this time"})


async def _handle_device_blacklist_check(_: Request) -> Response:
    """Device blacklist check."""
    return response_success_v3([])


def _include_product_iot_map_info(bot: dict[str, Any]) -> dict[str, Any]:
    if bumper_isc.mqtt_server is None:
        msg = "'bumper.mqtt_server' is None"
        raise Exception(msg)

    result = copy.deepcopy(bot)

    for botprod in get_product_iot_map():
        if botprod["classid"] == result["class"]:
            result["UILogicId"] = botprod["product"]["UILogicId"]
            result["ota"] = botprod["product"]["ota"]
            result["icon"] = botprod["product"]["iconUrl"]
            result["model"] = botprod["product"]["model"]
            result["pid"] = botprod["product"]["_id"]
            result["deviceName"] = botprod["product"]["name"]
            result["materialNo"] = botprod["product"]["materialNo"]
            result["product_category"] = "DEEBOT" if botprod["product"]["name"].startswith("DEEBOT") else "UNKNOWN"

            result["status"] = 1 if bot["mqtt_connection"] or bot["xmpp_connection"] else 0

            # TODO: improve as non static
            result["homeId"] = bumper_isc.HOME_ID
            result["homeSort"] = 1
            result["otaUpgrade"] = {}
            result["shareable"] = bool(bot["mqtt_connection"])
            result["sharedDevice"] = False
            result["updateInfo"] = {"changeLog": "", "needUpdate": False}

            if bot["mqtt_connection"]:
                # result["bindTs"] =
                result["offmap"] = True
                result["scode"] = {
                    "battery": True,
                    "charge": True,
                    "chargestate": True,
                    "clean": True,
                    "tmallstand": False,
                    "video": False,
                }

                sub_domain_suffix_2 = ""  # .dc-as
                sub_domain_suffix_4 = ""  # .dc
                sub_domain_suffix_ww = ""  # .ww

                result["service"] = {
                    "jmq": f"jmq-ngiot-eu{sub_domain_suffix_4}{sub_domain_suffix_ww}.ecouser.net",
                    "mqs": f"api-ngiot{sub_domain_suffix_2}{sub_domain_suffix_ww}.ecouser.net",
                }

            # mqtt_connection is not always set correctly, therefore workaround until fixed properly
            for session in bumper_isc.mqtt_server.sessions:
                if session.client_id is not None:
                    did = session.client_id.split("@")[0]
                    if did == bot["did"] and session.transitions.state == "connected":
                        result["status"] = 1
                        break
    return result
