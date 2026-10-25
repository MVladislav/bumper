"""Intl plugin module."""

import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request

from bumper.db import user_repo
from bumper.web.envelope import GL_V1, bind
from bumper.web.payloads import member_integral

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}intl/member/basicInfo")
@bind(GL_V1)
async def _handle_basic_info(request: Request) -> Any:
    """Get basic info."""
    user_dev_id = request.match_info.get("devid", "")
    user = user_repo.get_by_device_id(user_dev_id)
    if user is None:
        _LOGGER.warning(f"No user found for {user_dev_id}")
    else:
        return member_integral()

    raise HTTPInternalServerError


@routes.view(f"{BASE_URL}intl/member/signStatus")
@bind(GL_V1)
async def _handle_sign_status(_: Request) -> Any:
    """Sign. status."""
    return {"signStatus": "SIGN"}
