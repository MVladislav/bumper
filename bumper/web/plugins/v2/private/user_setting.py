"""User setting plugin module."""

from aiohttp import web

from bumper.web.plugins.v1.private.user_setting import handle_get_msg_receive_setting

from . import BASE_URL

routes = web.RouteTableDef()

routes.view(f"{BASE_URL}userSetting/getMsgReceiveSetting")(handle_get_msg_receive_setting)
