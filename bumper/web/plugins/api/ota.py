"""Ota plugin module."""

import base64
from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin

_LOGGER = logging.getLogger(__name__)


class OtaPlugin(WebserverPlugin):
    """Ota plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/ota/products/wukong/class/{class}/firmware/latest.json", _handle_products_firmware_latest),
        ]


async def _handle_products_firmware_latest(request: Request, todo: bool = False) -> Response:
    # TODO: check if we can implement a version update test to original server and if it makes sense
    if todo is False:
        return web.Response(status=404, body="Not Found")

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
