"""Global upload plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web import images
from bumper.web.plugins import WebserverPlugin


class GlobalPlugin(WebserverPlugin):
    """Global upload plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/global/{year}/{month}/{day}/{id}", images.get_bot_image),
        ]
