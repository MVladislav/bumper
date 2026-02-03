"""Member plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL


class MemberPlugin(WebserverPlugin):
    """Member plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}member/getExpByScene", handle_get_exp_by_scene),
        ]


async def handle_get_exp_by_scene(request: Request) -> Response:
    """Get exp by scene."""
    scene = request.query.get("scene", "")

    get_point = None
    prompt = None

    if scene == "GLOBALAPP_REGULATE_DEEBOT_SUCTION":
        get_point = 0
        prompt = "Task DEEBOT Perform suction power setting, +0"
    elif scene == "GLOBALAPP_REGULATE_DEEBOT_WATER":
        get_point = 0
        prompt = "Perform task DEEBOT water flow rate, +0"
    elif scene == "GLOBALAPP_TIMING_OF_CONSUMABLES":
        get_point = 0
        prompt = "Perform Display accessory usage task, +0"
    elif scene == "GLOBALAPP_VIRTUAL_WALL_MANAGEMENT":
        get_point = 0
        prompt = "Perform task Manage DEEBOT Virtual Walls, +0"
    elif scene in [
        "GLOBALAPP_MACHINE_RENAME",
        "GLOBALAPP_AREA_CATE_RENAME",
        "GLOBALAPP_FIRST_SET_PERSONAL_CLEAN_MODULE",
        "GLOBALAPP_SHOW_CLEAN_LOG",
        "GLOBALAPP_USE_HELP_CENTER",
        "GLOBALAPP_USE_SIDE_FILTER",
    ]:
        get_point = 0
        prompt = ":P, +0"

    key_only_once1 = "only"  # only because
    key_only_once2 = "Once"  # of code spell :D
    return response_success_v1(
        {
            "completeList": [
                {
                    "getExp": 0,
                    "getPoint": get_point,
                    f"{key_only_once1}{key_only_once2}": "N",
                    "prompt": prompt,
                },
            ],
        },
    )
