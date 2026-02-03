"""File plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.images import get_bot_image
from bumper.web.plugins import WebserverPlugin


class FilePlugin(WebserverPlugin):
    """Pim file plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/file/get/{id}", get_bot_image),
            web.route("*", "/api/pim/file/get/{id}", get_bot_image),
        ]
