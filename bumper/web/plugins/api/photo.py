"""Photo plugin module."""

from collections.abc import Iterable
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import photo_repo
from bumper.db.photos import KIND_MAP
from bumper.utils import map_image, utils
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3

_LOGGER = logging.getLogger(__name__)


class PhotoPlugin(WebserverPlugin):
    """Photo plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/photo/list", _handle_photo_list),
            web.route("*", "/photo/download", _handle_photo_download),
            web.route("*", "/photo/all", _handle_photo_delete_all),
        ]


async def _handle_photo_list(request: Request) -> Response:
    """List photos the robot uploaded."""
    try:
        limit = utils.to_int(request.query.get("limit"), 50)
        before = request.query.get("before")
        photo_type = request.query.get("type", "robot")
        mtype = request.query.get("mtype", "pic")
        did = request.query.get("did")

        records = photo_repo.list_by_did(did, limit=limit, before=utils.to_int(before))

        data: list[dict[str, Any]] = []
        for record in records:
            # `type` is `user` or `robot`, `mtype` is `pic` or `video`; an empty
            # value in the query means "do not filter on this field".
            if photo_type and record.get("type") != photo_type:
                continue
            if mtype and record.get("mtype") != mtype:
                continue
            data.append(
                {
                    "id": record.get("id", ""),
                    "size": record.get("size", 0),
                    "ts": record.get("ts", 0),
                    "did": record.get("did", ""),
                    "bindEvt": record.get("bindEvt", ""),
                    "type": record.get("type", "robot"),
                    "mtype": record.get("mtype", "pic"),
                },
            )

        return response_success_v3(data=data, result_key=None, include_success=True)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_photo_download(request: Request) -> Response:
    """Photo download."""
    try:
        photo_id = request.query.get("id", "")
        if not photo_id:
            return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")
        record = photo_repo.get_by_photo_id(photo_id)
        if record is None:
            return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")
        if record.get("kind") == KIND_MAP:
            map_data = photo_repo.decode_map(str(record.get("image", "")))
            image = map_image.render_map(map_data)
            if not image:
                return web.Response(status=404, body=b"", content_type="text/plain", charset="utf-8")
            return web.Response(body=image, content_type="image/png", charset="utf-8")
        image = photo_repo.decode_image(str(record.get("image", "")))
        return web.Response(body=image, content_type="image/jpeg", charset="utf-8")
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_photo_delete_all(_: Request) -> Response:
    """Delete every stored photo."""
    try:
        photo_repo.remove_all()
        return response_success_v3(result_key=None, include_success=True)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError
