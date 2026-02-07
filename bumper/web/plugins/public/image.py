"""Image plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_bot_image_path


class ImagePlugin(WebserverPlugin):
    """Image plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Image routes."""
        return [
            web.route("*", "/{id}/{image}", _get_bot_image),
        ]


async def _get_bot_image(_: Request) -> FileResponse:
    """Get generic image of bot."""
    return FileResponse(get_bot_image_path())
