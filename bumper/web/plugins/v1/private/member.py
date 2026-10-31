"""Member plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}member/getExpByScene")
@bind(GL_V1)
async def handle_get_exp_by_scene(request: Request) -> Any:
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
    return {
        "completeList": [
            {
                "getExp": 0,
                "getPoint": get_point,
                f"{key_only_once1}{key_only_once2}": "N",
                "prompt": prompt,
            },
        ],
    }
