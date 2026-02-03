"""User plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web import auth_util
from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.v1.private.user import handle_check_agreement_batch

from . import BASE_URL


class UserPlugin(WebserverPlugin):
    """User plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}user/login", auth_util.login),
            web.route("*", f"{BASE_URL}user/checkLogin", auth_util.login),
            web.route("*", f"{BASE_URL}user/checkAgreementBatch", handle_check_agreement_batch),
        ]
