"""Homed plugin module."""

import logging
from typing import Any
import uuid

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request

from bumper.db import token_repo, user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.context import read_body, verified_claims
from bumper.web.envelope import LEGACY, LEGACY_NO_RET, ApiError, bind
from bumper.web.payloads import (
    HOME_ROLE_IDS_NAMED,
    HomeInfo,
    home_infos,
    member_info,
    role_infos,
)

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/homed/home/list")
@bind(LEGACY_NO_RET)
async def _handle_home_list(request: Request) -> Any:
    """Home list."""
    user_id = request.query.get("userid")
    data: list[HomeInfo] = []
    if user_id is not None:
        user = user_repo.get_by_id(user_id)
        if user is not None:
            data = home_infos(user)
    return data


@routes.post(f"{PREFIX}/homed/home/create")
@bind(LEGACY_NO_RET)
async def _handle_home_create(request: Request) -> Any:
    """Home create."""
    utils.default_log_warn_not_impl("_handle_home_create")
    json_body = await read_body(request)
    jwt_info = verified_claims(request)
    if jwt_info is None:
        raise ApiError(msg="Auth error", code=1)

    name = json_body.get("name")
    token = token_repo.get_by_auth_code(jwt_info.get("auth_code", ""))
    if token and token.userid is not None:
        user_repo.add_home_id(token.userid, uuid.uuid4().hex)
        _LOGGER.debug(f"Create :: {name}")
    return None


@routes.view(f"{PREFIX}/homed/home/update")
@bind(LEGACY_NO_RET.with_optional_data())
async def _handle_home_update(request: Request) -> Any:
    """Home update."""
    utils.default_log_warn_not_impl("_handle_home_update")
    json_body = await read_body(request)
    home_id = json_body.get("homeId")
    name = json_body.get("name")
    _LOGGER.debug(f"Update :: homeId: {home_id} - name: {name}")
    return None


@routes.post(f"{PREFIX}/homed/home/delete")
@bind(LEGACY_NO_RET)
async def _handle_home_delete(request: Request) -> Any:
    """Home delete."""
    utils.default_log_warn_not_impl("_handle_home_delete")
    json_body = await read_body(request)
    home_id = str(json_body.get("homeId", ""))
    user = user_repo.get_by_home_id(home_id)
    if user is not None:
        user_repo.remove_home_id(user.userid, home_id)
    _LOGGER.debug(f"Delete :: {home_id}")
    return None


@routes.view(f"{PREFIX}/homed/member/list")
@bind(LEGACY_NO_RET)
async def _handle_member_list(request: Request) -> Any:
    """Member list."""
    home_id = request.query.get("homeId", bumper_isc.DEFAULT_HOME_ID)
    user = user_repo.get_by_home_id(home_id)
    if user is None:
        _LOGGER.warning(f"No user found for {home_id}")
    else:
        role_id, role_name = HOME_ROLE_IDS_NAMED[0]
        return [member_info(user, role_id, role_name)]

    raise HTTPInternalServerError


@routes.view(f"{PREFIX}/homed/home/role/list")
@bind(LEGACY_NO_RET)
async def _handle_home_role_list(_: Request) -> Any:
    """Home role list."""
    return role_infos()


@routes.view(f"{PREFIX}/homed/home/member/role/update")
@bind(LEGACY_NO_RET.with_optional_data())
async def _handle_home_member_role_update(request: Request) -> Any:
    """Update a member's home role."""
    _LOGGER.debug(f"Role update requested :: {await request.text()}")
    return None


@routes.view(f"{PREFIX}/homed/v2/matter/paa")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_matter_paa(_: Request) -> Any:
    """Matter / PAA integration probe."""
    _LOGGER.debug("Matter/PAA probe answered with an empty result")
    return {}


@routes.view(f"{PREFIX}/homed/v2/matter/fabric")
async def _handle_matter_fabric(_: Request) -> web.Response:
    """Return the response for a home without Matter-capable devices."""
    return web.json_response(
        {
            "code": 4007,
            "message": "There are no devices that support LAN mode under this username.",
        },
    )


@routes.post(f"{PREFIX}/homed/device/move")
@bind(LEGACY_NO_RET.with_optional_data())
async def _handle_device_move(request: Request) -> Any:
    """Device move."""
    post_body = await read_body(request)
    did = post_body.get("did")
    mid = post_body.get("mid")
    to = post_body.get("to")  # NOTE: possible home id
    _LOGGER.debug(f"Move :: did: {did} - mid: {mid} - to: {to}")

    return None
