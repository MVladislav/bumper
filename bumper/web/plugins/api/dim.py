"""Dim plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.mqtt.helper_bot import MQTTCommandModel
from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.api.iot import handle_commands


class DimPlugin(WebserverPlugin):
    """Dim plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/dim/devmanager.do", _handle_dev_manager),
        ]


async def _handle_dev_manager(request: Request) -> Response:
    """Dev Manager."""
    return await handle_commands(request, version=MQTTCommandModel.VERSION_OLD, extended_check=True)
