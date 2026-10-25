"""Global auth plugin module."""

from aiohttp import web

from bumper.web import auth_service
from bumper.web.envelope import GL_V1, bind

from . import PREFIX

routes = web.RouteTableDef()

routes.view(f"{PREFIX}/global/auth/getAuthCode")(bind(GL_V1)(auth_service.get_auth_code))
