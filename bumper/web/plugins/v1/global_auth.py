"""Global auth plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web import auth_service
from bumper.web.plugins import WebserverPlugin


class GlobalAuthPlugin(WebserverPlugin):
    """Global auth plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/global/auth/getAuthCode", auth_service.get_auth_code),
        ]
