"""Iot plugin module."""

from collections.abc import Iterable
import json
import logging
import random
import string

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import db, utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_error_v7

_LOGGER = logging.getLogger(__name__)


class IotPlugin(WebserverPlugin):
    """Iot plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "POST",
                "/iot/devmanager.do",
                _handle_devmanager_bot_command,
            ),
        ]


async def _handle_devmanager_bot_command(request: Request) -> Response:
    """Dev manager bot command."""
    try:
        if bumper_isc.mqtt_helperbot is None:
            msg = "'bumper.mqtt.helper_bot' is None"
            raise Exception(msg)

        json_body = json.loads(await request.text())

        # Its a command
        if (did := json_body.get("toId")) is not None:
            bot = db.bot_get(did)

            if bot is None:
                _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
                return web.json_response(
                    {
                        "ret": "fail",
                        "errno": 500,
                        "error": "requested bot is not found",
                        "debug": "requested bot is not found",
                    },
                )
            if bot.get("company", "") != "eco-ng":
                _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
                return web.json_response(
                    {
                        "ret": "fail",
                        "errno": 500,
                        "error": "requested bot is not supported",
                        "debug": "requested bot is not supported",
                    },
                )

            random_id = "".join(random.sample(string.ascii_letters, 4))
            body = await bumper_isc.mqtt_helperbot.send_command(json_body, random_id)
            _LOGGER.debug(f"Send Bot - {json_body}")
            _LOGGER.debug(f"Bot Response - {body}")

            # No response, send error back
            if body.get("resp") is None:
                _LOGGER.warning(
                    f"iot :: u:{request.query.get('u', '')} :: did:{did}"
                    f" :: cmd:{json_body.get('cmdName')} :: return non 'resp' :: {body}",
                )
            else:
                body.update({"payloadType": json_body.get("payloadType", "j")})

            return web.json_response(body)

        if (td := json_body.get("td")) is not None:
            if td == "PollSCResult":  # Seen when doing initial wifi config
                return web.json_response({"ret": "ok"})

            if td == "HasUnreadMsg":  # EcoVacs Home
                return web.json_response({"ret": "ok", "unRead": False})

            if td == "PreWifiConfig":  # EcoVacs Home
                return web.json_response({"ret": "ok"})

            _LOGGER.error(f"TD is not know :: {td} :: connected to MQTT")

    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    return response_error_v7()
