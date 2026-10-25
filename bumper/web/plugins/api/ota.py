"""Ota plugin module."""

import base64

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/ota/products/wukong/class/{{class}}/firmware/latest.json")
async def _handle_products_firmware_latest(request: Request) -> Response:
    """Return the firmware the robot runs.

    Bumper does not serve firmware, so the answer says that the robot runs the
    version it already has.
    """
    ver = request.query.get("ver", "0.0.0")
    module = request.query.get("module", "fw0")
    data = {
        "version": ver,
        "name": "wukong",
        "force": False,
        module: {
            "force": False,
            "version": ver,
            "size": 0,
            "checkSum": None,
            "changeLog": base64.b64encode(b"You are running on bumper, here will no update be provided!").decode("utf-8"),
            "extra": {},
            "url": None,
            "urls": [],
        },
    }
    return web.json_response(data)
