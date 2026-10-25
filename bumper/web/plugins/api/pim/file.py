"""File plugin module."""

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request

from bumper.web.static_api import get_bot_image_path

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/file/get/{{id}}")
@routes.view(f"{PREFIX}/api/pim/file/get/{{id}}")
async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())
