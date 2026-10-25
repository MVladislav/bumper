"""Common plugin module."""

from aiohttp import web

from bumper.web.plugins.v2.private.common import handle_get_bottom_navigate_info_list

from . import BASE_URL

routes = web.RouteTableDef()

routes.view(f"{BASE_URL}common/getBottomNavigateInfoList")(handle_get_bottom_navigate_info_list)
