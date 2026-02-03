"""Dln plugin module."""

from collections.abc import Iterable
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo, clean_log_repo
from bumper.utils import utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v3

_LOGGER = logging.getLogger(__name__)


class DlnPlugin(WebserverPlugin):
    """Dln plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/dln/api/log/clean_result/list", _handle_clean_result_list),
            web.route("*", "/dln/api/log/clean_result/del", _handle_clean_result_del),
        ]


async def _handle_clean_result_list(request: Request) -> Response:
    """Clean result list."""
    try:
        did: str | None = request.query.get("did")
        log_type: str = request.query.get("logType", "")
        data = []

        if did is None:
            _LOGGER.error("No DID specified :: connected to MQTT")
        elif log_type == "clean":
            bot = bot_repo.get(did)
            if bot is None or bot.company != "eco-ng":
                _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
            else:
                clean_logs = clean_log_repo.list_by_did(did)
                for clean_log in clean_logs:
                    log = clean_log.as_dict()
                    log.update({"did": did})
                    data.append(log)

        return response_success_v3(data=sorted(data, key=lambda x: x["ts"], reverse=True))
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_clean_result_del(request: Request) -> Response:
    """Clean result delete."""
    json_data: dict[str, Any] = await request.json()
    log_ids: list[str] = json_data.get("logIds", [])
    for log_id in log_ids:
        clean_log_repo.remove_by_id(log_id)
    return response_success_v3(data=None)
