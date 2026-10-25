"""Message plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}message/hasMoreUnReadMsg")
@routes.view(f"{BASE_URL}/message/hasMoreUnReadMsg")
@bind(GL_V1)
async def _handle_has_more_unread_message(_: Request) -> Any:
    """Has more unread message."""
    return {"moreUnReadMsg": "N"}


@routes.view(f"{BASE_URL}message/waterfallFlow")
@bind(GL_V1)
async def _handle_waterfall_flow(_: Request) -> Any:
    """Message waterfall flow."""
    return {"list": []}


@routes.view(f"{BASE_URL}message/moduleConfiguration")
@bind(GL_V1)
async def _handle_module_configuration(_: Request) -> Any:
    """Message module configuration."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return {
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
    }
