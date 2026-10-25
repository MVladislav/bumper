"""Dim plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.mqtt.helper_bot import MQTTCommandModel
from bumper.web.plugins.api.iot import handle_commands

from . import PREFIX

routes = web.RouteTableDef()


@routes.post(f"{PREFIX}/dim/devmanager.do")
async def _handle_dev_manager(request: Request) -> Response:
    """Dev Manager."""
    return await handle_commands(request, version=MQTTCommandModel.VERSION_OLD, extended_check=True)
