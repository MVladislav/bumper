"""Image plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web import images
from bumper.web.plugins import WebserverPlugin


class ImagePlugin(WebserverPlugin):
    """Image plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Image routes."""
        return [
            web.route("*", "/{id}/{image}", images.get_bot_image),
        ]
