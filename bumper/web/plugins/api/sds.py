"""Sds plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils import utils
from bumper.web.envelope import LEGACY, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/sds/baidu/audio/getcred")
@bind(LEGACY.with_result(None).with_success(True))
async def _handle_baidu_audio_getcred(_: Request) -> Any:
    utils.default_log_warn_not_impl("_handle_baidu_audio_getcred")
    return None
