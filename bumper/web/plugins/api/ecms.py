"""Ecms plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request

from bumper.utils.settings import config as bumper_isc
from bumper.web.context import read_body
from bumper.web.envelope import LEGACY, ApiError, bind
from bumper.web.hosts import api_host
from bumper.web.static_api import get_bot_image_path

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/ecms/file/get/{{id}}")
async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())


@routes.view(f"{PREFIX}/ecms/app/ad/res")
@routes.view(f"{PREFIX}/ecms/app/ad/res/v2")
@routes.view(f"{PREFIX}/ecms/app/ad/res/V2")
@routes.view(f"{PREFIX}/ecms/app/ad/res/v3")
@routes.view(f"{PREFIX}/ecms/app/ad/res/v3/")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_ad_res(_: Request) -> Any:
    """Ad res."""
    return []


@routes.view(f"{PREFIX}/ecms/app/element/hint")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_hint(request: Request) -> Any:
    """Hint."""
    codes = request.query.get("codes", "").split(",")
    data = {}
    for code in codes:
        data[code] = False
    return data


@routes.view(f"{PREFIX}/ecms/app/resources")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_resources(request: Request) -> Any:
    """Resources."""
    locations = request.query.get("locations", "")
    lang = request.query.get("lang", "en").lower()
    data: list[dict[str, Any]] = []

    if locations == "home_manage_intro":
        data = []
    elif locations == "robotui_func_ops":
        domain1 = api_host("adv-app", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)
        domain2 = api_host("api-app", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1)
        data = [
            {
                "action": {
                    "clickAction": "1",
                    "clickURL": f"https://{domain1}/pim/yiko_scene_newton.html?lang={lang}&defaultLang={lang}",
                },
                "content": f"https://{domain2}/api/ecms/file/get/62206001e50121388401de95",
                "description": "",
                "location": "robotui_func_ops",
                "resId": "622060a8e5012100b501e004",
                "tags": [
                    "n4gstt",
                    "3yqsch",
                    "p95mgv",
                    "jtmf04",
                    "lx3j7m",
                    "bro5wu",
                    "1vxt52",
                    "85nbtp",
                    "p1jij8",
                    "9ku8nu",
                    "2gab4o",
                ],
                "title": "",
                "type": "svga",
            },
        ]
    elif locations == "robot_setting_yiko_ops":
        data = [
            {
                "resId": "61ceb7d1312d7c02f3b5f047",  # pragma: allowlist secret
                "location": "robot_setting_yiko_ops",
                "title": "",
                "description": "",
                "type": "jsonObject",
                "action": {"clickAction": "0", "clickURL": ""},
                "tags": [],
                "content": [
                    "\u201cStart cleaning\u201d",
                    "\u201cPause task\u201d",
                    "\u201cTurn to standard mode\u201d",
                    "\u201cHave consumables expired?\u201d",
                    "\u201cCurrent flow mode\u201d",
                ],
            },
        ]
    else:
        _LOGGER.warning(f"locations is not know :: {locations}")
    return data


@routes.view(f"{PREFIX}/ecms/app/push/event")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_push_event(request: Request) -> Any:
    """Push Event."""
    data_category = request.query.get("dataCategory", "")
    resource_id = request.query.get("resourceId", "")
    if not data_category or not resource_id:
        msg = "request params missing: dataCategory or resourceId"
        raise ApiError(msg=msg, code=500)

    return "ok"


@routes.view(f"{PREFIX}/ecms/app/user/theme")
@bind(LEGACY.with_result(None).with_success(True).with_optional_data())
async def _handle_user_theme(_: Request) -> Any:
    """User Theme."""
    return None


@routes.view(f"{PREFIX}/ecms/app/user/theme/enabled")
@bind(LEGACY.with_result(None).with_success(True).with_optional_data())
async def _handle_user_theme_enabled(request: Request) -> Any:
    """Whether the user theme is enabled."""
    if request.method == "PUT":
        await read_body(request)
        return None
    return {"enabled": True}
