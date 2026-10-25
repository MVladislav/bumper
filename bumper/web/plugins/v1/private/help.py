"""Help plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.envelope import GL_V1, bind
from bumper.web.payloads import help_index, help_product_index

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}help/getHelpIndex")
@bind(GL_V1)
async def _handle_get_help_index(_: Request) -> Any:
    """Get help index."""
    return help_index()


@routes.view(f"{BASE_URL}help/getProductHelpIndex")
@bind(GL_V1)
async def _handle_get_product_help_index(_: Request) -> Any:
    """Get product help index."""
    return help_product_index()
