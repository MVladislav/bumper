"""Pim Event Detail plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2

from bumper.utils.device_errors import DEVICE_ERRORS_BY_CODE, describe, recommendation
from bumper.web.static_api import get_event_detail

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/eventdetail.html")
async def _handle_event_detail(request: Request) -> Response:
    """Show a locally mapped robot error, or the default detail document."""
    if "errcode" in request.query:
        raw_code = request.query.get("errcode", "")
        try:
            code = int(raw_code)
        except ValueError:
            code = None
        error = DEVICE_ERRORS_BY_CODE.get(code) if code is not None else None
        return aiohttp_jinja2.render_template(
            "device_error.jinja2",
            request,
            {
                "code": raw_code,
                "class_id": request.query.get("class", ""),
                "language": request.query.get("lang", "en"),
                "description": describe(code) if code is not None else "Unrecognized error code",
                "name": error.name if error else "Unknown device error",
                "recommendation": recommendation(code),
                "known": error is not None,
            },
        )
    return web.Response(text=get_event_detail(), content_type="text/html")
