"""Lg plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.db import bot_repo, clean_log_repo, photo_repo
from bumper.db.photos import KIND_MAP
from bumper.utils import map_doc, utils
from bumper.web.context import read_body
from bumper.web.envelope import ERROR_TODO_RET_RET
from bumper.web.hosts import photo_url

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.post(f"{PREFIX}/lg/log.do")
async def _handle_lg_log(request: Request) -> Response:
    """Clean result list."""
    try:
        json_body = await read_body(request)
        did: str | None = json_body.get("did")
        td: str = json_body.get("td", "")
        logs: list[dict[str, Any]] = []

        if did is None:
            _LOGGER.error("No DID specified :: connected to MQTT")
        elif td == "GetCleanedMap":
            # The app asks for the map of a finished clean, keyed by the did and
            # a timestamp in milliseconds truncated to whole seconds. The map
            # itself is what the robot uploaded to the data-collect endpoint.
            bot = bot_repo.get_by_did_or_name(did)
            device_id = bot.did if bot is not None and bot.did else did
            map_data = _stored_map(device_id, _map_timestamp(json_body.get("ets")))
            if map_data is None:
                _LOGGER.info(f"No map stored for did={did}")
            # The app reads the pieces of the map and the driven path from the
            # top level of the answer, so they are not wrapped in a field.
            return web.json_response({"ret": "ok", **map_doc.cleaned_map(map_data)})
        elif td == "GetCleanLogs":
            bot = bot_repo.get_by_did_or_name(did)
            if bot is None or bot.company != "eco-ng":
                _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
            else:
                device_id = bot.did or did
                clean_logs = clean_log_repo.list_by_did(device_id)
                maps = photo_repo.maps_for_logs(clean_log_repo.list_by_did(device_id))
                for clean_log in clean_logs:
                    entry = clean_log.as_dict()
                    if photo_id := maps.get(clean_log.clean_log_id):
                        entry["imageUrl"] = photo_url(request.host, photo_id)
                    logs.append(entry)

        return web.json_response(
            {
                "ret": "ok",
                "logs": sorted(logs, key=lambda x: x["ts"], reverse=True),
            },
        )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    return web.json_response(ERROR_TODO_RET_RET.render(1, "unknown"))


def _map_timestamp(ets: Any) -> int | None:
    """Return the `ets` value of a map request as a millisecond timestamp.

    The app truncates the timestamp to whole seconds before sending it, so the
    stored maps are compared against the second it names.
    """
    timestamp = utils.to_int(ets)
    return timestamp if timestamp is not None else None


def _stored_map(did: str, at_ms: int | None) -> dict[str, Any] | None:
    """Return the map the robot uploaded for a device, if there is one."""
    records = photo_repo.list_by_did(did, limit=100, kind=KIND_MAP)
    if at_ms is not None:
        records = [record for record in records if (utils.to_int(record.get("ts"), 0) or 0) <= at_ms]
    if not records:
        return None
    return photo_repo.decode_map(str(records[0].get("image", "")))
