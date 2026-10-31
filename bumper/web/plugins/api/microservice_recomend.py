"""Microservice recommend plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import LEGACY, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/microservice-recomend/userReminderResult/")
@bind(LEGACY.with_result(None).with_success(True).with_optional_data())
async def _handle_user_reminder_result(_: Request) -> Any:
    """User reminder result."""
    return None
