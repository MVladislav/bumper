"""User setting plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.v1.private.user_setting import handle_get_msg_receive_setting

from . import BASE_URL


class UserSettingPlugin(WebserverPlugin):
    """User setting plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}userSetting/getMsgReceiveSetting", handle_get_msg_receive_setting),
        ]
