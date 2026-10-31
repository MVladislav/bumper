"""Dln plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.db import bot_repo, clean_log_repo, photo_repo
from bumper.db.photos import KIND_MAP
from bumper.utils import map_image, utils
from bumper.web.envelope import LEGACY, LEGACY_NO_RET, bind
from bumper.web.hosts import photo_url, placeholder_photo_url

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/dln/api/log/clean_result/list")
@bind(LEGACY_NO_RET)
async def _handle_clean_result_list(request: Request) -> Any:
    """Clean result list."""
    did: str | None = request.query.get("did")
    log_type: str = request.query.get("logType", "clean")
    size: int = utils.to_int(request.query.get("size"), 10) or 10
    before: int | None = utils.to_int(request.query.get("before"))
    data = []

    if did is None:
        _LOGGER.error("No DID specified :: connected to MQTT")
    elif log_type == "clean":
        bot = bot_repo.get_by_did_or_name(did)
        if bot is None or bot.company != "eco-ng":
            _LOGGER.error(f"No bots with DID :: {did} :: connected to MQTT")
        else:
            device_id = bot.did or did
            clean_logs = clean_log_repo.list_by_did(device_id)
            # The app pages backwards through the jobs.
            if before is not None:
                clean_logs = [log for log in clean_logs if (utils.to_int(log.ts, 0) or 0) < before]
            # The picture of a job is the map the robot uploaded when the job was done.
            maps = photo_repo.maps_for_logs(clean_log_repo.list_by_did(device_id))
            for clean_log in clean_logs:
                log = clean_log.as_dict()
                log.update({"did": did})
                if photo_id := maps.get(clean_log.clean_log_id):
                    log["imageUrl"] = photo_url(request.host, photo_id)
                else:
                    log["imageUrl"] = placeholder_photo_url(request.host)
                data.append(log)

    return sorted(data, key=lambda x: x["ts"], reverse=True)[:size]


@routes.view(f"{PREFIX}/dln/api/log/clean_result/data")
async def _handle_clean_result_data(request: Request) -> Response:
    """Return the saved map associated with a clean result."""
    clean_log_id = request.query.get("id", "")
    clean_log = clean_log_repo.list_by_id(clean_log_id) if clean_log_id else None
    if clean_log is None:
        return _not_found()

    logs = clean_log_repo.list_by_did(clean_log.did or "")
    photo_id = photo_repo.maps_for_logs(logs).get(clean_log.clean_log_id)
    photo = photo_repo.get_by_photo_id(photo_id) if photo_id else None
    if photo is None or photo.get("kind") != KIND_MAP:
        return _not_found()

    map_data = photo_repo.decode_map(str(photo.get("image", "")))
    image = map_image.render_map_svg(map_data)
    if not image:
        return _not_found()
    return web.Response(body=image, content_type="image/svg+xml")


@routes.view(f"{PREFIX}/dln/api/log/clean_result/del")
@bind(LEGACY)
async def _handle_clean_result_del(request: Request) -> Any:
    """Clean result delete."""
    json_data: dict[str, Any] = await request.json()
    log_ids: list[str] = json_data.get("logIds", [])
    for log_id in log_ids:
        clean_log_repo.remove_by_id(log_id)
    return None


def _not_found() -> Response:
    """Return an empty response when a clean result or map is absent."""
    return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")
