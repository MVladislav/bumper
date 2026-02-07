"""Ecms plugin module."""

from collections.abc import Iterable
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_bot_image_path
from bumper.web.utils.response_helper import response_success_v3

_LOGGER = logging.getLogger(__name__)


class EcmsPlugin(WebserverPlugin):
    """Ecms plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/ecms/file/get/{id}", _get_bot_image),  # TODO: real response is a svga response
            web.route("*", "/ecms/app/ad/res", _handle_ad_res),
            web.route("*", "/ecms/app/ad/res/v2", _handle_ad_res),
            web.route("*", "/ecms/app/ad/res/v3", _handle_ad_res),
            web.route("*", "/ecms/app/element/hint", _handle_hint),
            web.route("*", "/ecms/app/resources", _handle_resources),
            web.route("*", "/ecms/app/push/event", _handle_push_event),
        ]


async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())


async def _handle_ad_res(_: Request) -> Response:
    """Ad res."""
    return response_success_v3(data=[], result_key=None, include_success=True)


async def _handle_hint(request: Request) -> Response:
    """Hint."""
    codes = request.query.get("codes", "").split(",")
    data = {}
    for code in codes:
        data[code] = False
    return response_success_v3(data=data, result_key=None, include_success=True)


async def _handle_resources(request: Request) -> Response:
    """Resources."""
    locations = request.query.get("locations", "")
    lang = request.query.get("lang", "en").lower()
    data: list[dict[str, Any]] = []

    if locations == "home_manage_intro":
        data = []
    elif locations == "robotui_func_ops":
        domain1 = f"adv-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
        domain2 = f"api-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
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
    elif locations == "home_manage_intro":
        data = []

    if len(data) <= 0:
        _LOGGER.warning(f"locations is not know :: {locations}")
    return response_success_v3(data=data, result_key=None, include_success=True)


async def _handle_push_event(_: Request) -> Response:
    """Ad res."""
    # dataCategory = request.query.get("dataCategory", "Discover-Hint")
    # resourceId = request.query.get("resourceId", "Robot")
    return response_success_v3(data="ok", result_key=None, include_success=True)
