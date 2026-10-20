"""Iot plugin module."""

from collections.abc import Iterable
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import MQTTCommandModel
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.models import VacBotDevice
from bumper.web.utils.response_helper import (
    response_error_v7,
    response_error_v8,
    response_ngiot_offline,
)

_LOGGER = logging.getLogger(__name__)


class IotPlugin(WebserverPlugin):
    """Iot plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/iot/devmanager.do", _handle_devmanager_bot_command),
            web.route("POST", "/iot/endpoint/control", _handle_endpoint_control),
            web.route("POST", "/iot/endpoint/control/v2", _handle_endpoint_control),
        ]


async def _handle_devmanager_bot_command(request: Request) -> Response:
    """Dev manager bot command."""
    return await handle_commands(request, version=MQTTCommandModel.VERSION_OLD)


async def _handle_endpoint_control(request: Request) -> Response:
    """Endpoint control bot command."""
    return await handle_commands(request, version=MQTTCommandModel.VERSION_NEW)


def _bot_mqtt_connected(bot: VacBotDevice) -> bool | None:
    """Report whether the bot currently holds a session on the MQTT broker."""
    mqtt_server = bumper_isc.mqtt_server
    if mqtt_server is None or mqtt_server.state != "started":
        return None

    expected_client_id = f"{bot.did}@{bot.class_id}/{bot.resource}"
    return any(session.client_id == expected_client_id for session in mqtt_server.sessions)


async def handle_commands(
    request: Request,
    version: str = MQTTCommandModel.VERSION_OLD,
    extended_check: bool = False,
) -> Response:
    """Handle commands."""
    try:
        if bumper_isc.mqtt_helperbot is None:
            msg = "'bumper_isc.mqtt_helperbot' is None"
            raise Exception(msg)

        json_body: dict[str, Any] = {}
        if version == MQTTCommandModel.VERSION_OLD:
            json_body = json.loads(await request.text())
        elif version == MQTTCommandModel.VERSION_NEW:
            json_body = dict(request.query)
            json_body.update({"payload": json.loads(await request.text())})
        else:
            _LOGGER.warning(f"MQTT command version not known :: '{version}'")
        cmd_request = MQTTCommandModel(cmdjson=json_body, version=version)

        # Its a command
        if cmd_request.did is not None:
            if (bot := bot_repo.get(cmd_request.did)) is None:
                _LOGGER.warning(f"No bots with DID :: {cmd_request.did} :: connected to MQTT")
                return response_error_v8(cmd_request.request_id, "requested bot is not supported")
            if bot.company != "eco-ng":
                _LOGGER.warning(f"No bots with DID :: {cmd_request.did} :: connected to MQTT")
                return response_error_v8(cmd_request.request_id, "requested bot is not supported")

            # Answer "offline" straight away rather than publishing.
            if version == MQTTCommandModel.VERSION_NEW and _bot_mqtt_connected(bot) is False:
                _LOGGER.info(f"Bot {cmd_request.did} is not connected to MQTT :: reporting endpoint offline")
                return response_ngiot_offline(cmd_request.request_id)

            if extended_check and (bot.company != "eco-ng" or not bot.mqtt_connection):
                _LOGGER.warning(f"No bots with DID :: {cmd_request.did} :: connected to MQTT")
                return response_error_v8(cmd_request.request_id, "requested bot is not supported")

            return await bumper_isc.mqtt_helperbot.send_command(cmd_request)

        if cmd_request.td is not None:
            if cmd_request.td == "PollSCResult":  # Seen when doing initial wifi config
                # TODO: check how to use "sck" in request info
                return web.json_response(
                    {
                        "ret": "ok",  # TODO: extend below
                        # "did": "DID",
                        # "type": "CLASS",
                        # "resource": "RESOURCE",
                        # "name": "USERNAME",
                    },
                )
            if cmd_request.td == "HasUnreadMsg":  # EcoVacs Home
                return web.json_response({"ret": "ok", "unRead": False})
            if cmd_request.td.startswith("PreWifiConfig"):
                return web.json_response({"ret": "ok"})
            _LOGGER.warning(f"TD is not know :: {cmd_request.td} :: connected to MQTT")

    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    return response_error_v7()
