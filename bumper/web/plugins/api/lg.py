"""Lg plugin module."""

from collections.abc import Iterable
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo, clean_log_repo
from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_error_v7

_LOGGER = logging.getLogger(__name__)


class LgPlugin(WebserverPlugin):
    """Lg plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/lg/log.do", _handle_lg_log),
        ]


async def _handle_lg_log(request: Request) -> Response:
    """Clean result list."""
    try:
        json_body: dict[str, Any] = json.loads(await request.text())
        did: str | None = json_body.get("did")
        td: str = json_body.get("td", "")
        logs: list[dict[str, Any]] = []

        if did is None:
            _LOGGER.error("No DID specified :: connected to MQTT")
        elif td == "GetCleanLogs":
            bot = bot_repo.get(did)
            if bot is None or bot.company != "eco-ng":
                _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
            else:
                clean_logs = clean_log_repo.list_by_did(did)
                logs.extend(clean_log.as_dict() for clean_log in clean_logs)

        return web.json_response(
            {
                "ret": "ok",
                "logs": sorted(logs, key=lambda x: x["ts"], reverse=True),
            },
        )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    return response_error_v7()
