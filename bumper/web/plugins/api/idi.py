"""Idi plugin module.

The "idi" api is the one the newer app of the robot uses.
"""

import json
import logging
from typing import Any
from urllib.parse import unquote

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.db import bot_repo, clean_log_repo, photo_repo
from bumper.db.photos import KIND_MAP, KIND_PICTURE
from bumper.utils import map_doc, utils
from bumper.utils.settings import config as bumper_isc
from bumper.utils.utils import to_milliseconds
from bumper.web.envelope import ApiError
from bumper.web.utils.models import CleanLog

from . import PREFIX

_LOGGER = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.route("*", f"{PREFIX}/idi/data_collect/upload/generalData")
async def _handle_idi_data_collect(request: Request) -> Response:
    """Upload the data of a job.

    The app posts the clean log of a finished job here: the map of the job,
    the driven path and the statistics of the run.
    """
    return await handle_data_collect(request)


async def handle_data_collect(request: Request) -> Response:
    """Handle data collect (/data_collect/upload/generalData or /api/idi/data_collect/upload/generalData).

    The device POSTs the raw payload with the metadata in the query string

    Two kinds of payload arrive on this endpoint. A picture is a raw JPEG; a
    cleaned map is a JSON document. The two are stored apart, because the app
    reads them back through different endpoints: pictures through
    `/api/photo/*`, maps through `lg/log.do` with `td: "GetCleanedMap"`.
    """
    try:
        did = request.query.get("auth.did", "")
        bot = bot_repo.get_by_did_or_name(did) if did else None
        if bot is None:
            _LOGGER.warning(f"Upload for unknown bot :: did={did}")
        # Some robots send the serial number where the others send the device ID.
        device_id = bot.did if bot is not None and bot.did else did

        meta = _parse_upload_meta(request.query.get("meta", ""))
        bind_evt = str(meta.get("bindEvt", "cruise"))
        if bind_evt not in {"cruise", "findPet"}:
            _LOGGER.warning(f"Upload with unknown bindEvt :: {bind_evt}")

        if bot is not None:
            mismatches = [
                field
                for field, expected, actual in (
                    ("name", bot.name, request.query.get("auth.name", "")),
                    ("mid", bot.class_id, request.query.get("auth.mid", "")),
                    ("res", bot.resource, request.query.get("auth.res", "")),
                )
                if expected and actual and expected != actual
            ]
            if mismatches:
                _LOGGER.warning(f"Upload identity mismatch :: did={did} :: fields={mismatches}")

        payload = await request.read()
        # The robot sends the time of a picture in milliseconds and the time of
        # a map in seconds, so the time is scaled up to milliseconds.
        ts = to_milliseconds(utils.to_int(meta.get("ts"), utils.to_int(request.query.get("auth.ts"), 0) * 1000))

        _LOGGER.info(
            f"Upload :: did={did} :: bindEvt={bind_evt} :: bindID={meta.get('bindID', '')} "
            f":: bytes={len(payload)} :: sign={request.query.get('auth.sign', '')}",
        )

        if payload:
            photo_id = f"{ts}{device_id}" if ts else device_id
            kind = KIND_MAP if _is_map_payload(payload) else KIND_PICTURE
            # The newer upload of the app carries the clean log of the job,
            # with the map of the job in it.
            if kind == KIND_MAP:
                _store_clean_log(device_id, request.query.get("auth.res", ""), payload)
            document = _map_document_of(payload) if kind == KIND_MAP else payload
            photo_repo.add(
                {
                    "id": photo_id,
                    "did": device_id,
                    "ts": ts,
                    "size": len(payload),
                    "bindEvt": bind_evt,
                    "bindID": str(meta.get("bindID", "")),
                    "type": "robot",
                    "mtype": "pic",
                    "kind": kind,
                    "image": photo_repo.encode_image(document),
                },
            )
            photo_repo.prune(device_id, bumper_isc.PHOTO_MAX_PER_DEVICE)
            _LOGGER.info(f"Upload stored :: id={photo_id} :: kind={kind}")

        return web.Response(body=b"", content_type="text/plain", charset="utf-8")
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


def _parse_upload_meta(raw: str) -> dict[str, Any]:
    """Parse the `meta` query parameter, which is a URL-encoded JSON object."""
    if not raw:
        return {}
    try:
        parsed = json.loads(unquote(raw))
    except (ValueError, UnicodeDecodeError):
        _LOGGER.warning("Camera upload meta is not valid URL-encoded JSON")
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _store_clean_log(did: str, rid: str, payload: bytes) -> None:
    """Store the statistics of a job the upload carries, if it carries them."""
    if not did:
        return
    try:
        document = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return
    if not isinstance(document, dict):
        return

    stats = document.get("stats")
    if not isinstance(stats, dict) or stats.get("start") is None:
        return

    data = dict(stats)
    # The upload measures the area in square millimetres, the app shows it in
    # square metres.
    area = utils.to_int(data.get("area"))
    if area is not None and area > 10000:
        data["area"] = area // 10000

    clean_log_repo.add_or_update(CleanLog.from_dict(did=did, rid=rid, data=data))


def _map_document_of(payload: bytes) -> bytes:
    """Return the map document of an upload of a map.

    The newer upload of the app carries the clean log of the job, with the
    map of the job in it. The document of the map is what the app reads.
    """
    try:
        parsed = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return payload
    if not isinstance(parsed, dict):
        return payload
    return json.dumps(map_doc.normalise_map_document(parsed)).encode("utf-8")


def _is_map_payload(payload: bytes) -> bool:
    """Return whether an upload carries a map document rather than a picture."""
    return payload.lstrip()[:1] == b"{"
