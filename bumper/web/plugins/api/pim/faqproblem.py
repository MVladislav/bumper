"""Pim FAQ problem plugin module."""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.web.static_api import get_faq_problem

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/faqproblem.html")
async def _handle_faq_problem(_: Request) -> Response:
    """Handle FAQ problem."""
    return web.Response(text=get_faq_problem(), content_type="text/html")
