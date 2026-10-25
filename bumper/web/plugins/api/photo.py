"""Photo plugin module."""

from importlib.resources import files
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.db import photo_repo
from bumper.db.photos import KIND_MAP
from bumper.utils import map_image, utils
from bumper.web.envelope import LEGACY, LEGACY_NO_RET, bind

from . import PREFIX

_PHOTO_PLACEHOLDER = files("bumper.web").joinpath("static_web", "no-map.svg").read_bytes()


def _photo_placeholder() -> Response:
    """Return the shared placeholder when a photo or map cannot be rendered."""
    return web.Response(body=_PHOTO_PLACEHOLDER, content_type="image/svg+xml")


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/photo/list")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_photo_list(request: Request) -> Any:
    """List photos the robot uploaded."""
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

    return data


@routes.view(f"{PREFIX}/photo/download")
async def _handle_photo_download(request: Request) -> Response:
    """Photo download."""
    photo_id = request.query.get("id", "")
    if not photo_id:
        return _photo_placeholder()
    record = photo_repo.get_by_photo_id(photo_id)
    if record is None:
        return _photo_placeholder()
    if record.get("kind") == KIND_MAP:
        map_data = photo_repo.decode_map(str(record.get("image", "")))
        image = map_image.render_map_svg(map_data)
        if not image:
            return _photo_placeholder()
        return web.Response(body=image, content_type="image/svg+xml")
    image = photo_repo.decode_image(str(record.get("image", "")))
    return web.Response(body=image, content_type="image/jpeg", charset="utf-8")


@routes.view(f"{PREFIX}/photo/all")
@bind(LEGACY_NO_RET.with_success(True))
async def _handle_photo_delete_all(_: Request) -> Any:
    """Delete every stored photo."""
    photo_repo.remove_all()
    return None
