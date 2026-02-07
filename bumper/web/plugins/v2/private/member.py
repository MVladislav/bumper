"""Member plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.v1.private.member import handle_get_exp_by_scene
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class MemberPlugin(WebserverPlugin):
    """Member plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}member/getExpByScene", handle_get_exp_by_scene),
            web.route("*", f"{BASE_URL}member/getBindBenefit", _handle_get_bind_benefit),
        ]


async def _handle_get_bind_benefit(_: Request) -> Response:
    """Get bind benefit."""
    return response_success_v1({"completeList": []})
