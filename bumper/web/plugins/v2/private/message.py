"""Message plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class MessagePlugin(WebserverPlugin):
    """Message plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}message/hasMoreUnReadMsg", _handle_has_more_unread_message),
            web.route("*", f"{BASE_URL}message/waterfallFlow", _handle_waterfall_flow),
            web.route("*", f"{BASE_URL}message/moduleConfiguration", _handle_module_configuration),
        ]


async def _handle_has_more_unread_message(_: Request) -> Response:
    """Has more unread message."""
    return response_success_v1({"moreUnReadMsg": "N"})


async def _handle_waterfall_flow(_: Request) -> Response:
    """Message waterfall flow."""
    return response_success_v1({"list": []})


async def _handle_module_configuration(_: Request) -> Response:
    """Message module configuration."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return response_success_v1(
        {
            "list": [
                {
                    "icon": f"{domain}/2021/11/24/20211124063251_b87eda89effe37115d1812af65aef03c.png",
                    "id": "20211124153947_8e4efefa3eb46b424a6fab894239679b",
                    "lastUnReadMsgType": None,
                    "moduleName": "Promotion messages",
                    "moduleType": "ACTIVITY",
                    "moreUnReadMsg": "N",
                    "sort": 2000,
                    "tip": None,
                },
                {
                    "icon": f"{domain}/2021/11/24/20211124063334_59849310e3a426ae9b8f190f1210c6d5.png",
                    "id": "20211124153947_94355558fb85f05d182fb73f91222a3b",
                    "lastUnReadMsgType": None,
                    "moduleName": "Service notifications",
                    "moduleType": "SERVICE_NOTIFICATION",
                    "moreUnReadMsg": "N",
                    "sort": 3000,
                    "tip": None,
                },
                {
                    "icon": f"{domain}/2021/11/24/20211124063217_b8e8aca3588d70304b97708b88e7e415.png",
                    "id": "20211124153947_c9d40a1be9cbefb15c67a91ab4bc52d9",
                    "lastUnReadMsgType": None,
                    "moduleName": "Sharing Message",
                    "moduleType": "SHARE_MESSAGE",
                    "moreUnReadMsg": "N",
                    "sort": 4000,
                    "tip": None,
                },
            ],
        },
    )
