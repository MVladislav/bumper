"""Neng plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v3, response_success_v4


class NengPlugin(WebserverPlugin):
    """Neng plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", "/neng/message/hasUnreadMsg", _handle_has_unread_message),
            web.route("*", "/neng/message/getShareMsgs", _handle_get_share_msgs),
            web.route("*", "/neng/message/getlist", _handle_get_list),
            web.route("*", "/neng/message/read", _handle_read),
            web.route("*", "/neng/v2/message/push", _handle_v2_message_push),
            web.route("*", "/neng/v3/message/pushStatus", _handle_v3_message_push_status),
            web.route("*", "/neng/v3/message/latest_by_did", _handle_v3_latest_by_did),
            web.route("*", "/neng/v3/message/list", _handle_v3_message_list),
            web.route("*", "/neng/v3/product/msg/tabs", _handle_v3_product_msg_tabs),
            web.route("*", "/neng/v3/shareMsg/hasUnreadMsg", _handle_v3_share_msg_has_unread_msg),
        ]


async def _handle_has_unread_message(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v4({"hasUnRead": False, "shareMsgUnRead": False})


async def _handle_get_share_msgs(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v4({"hasNext": False, "msgs": []})


async def _handle_get_list(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v4({"hasNext": False, "msgs": []})


async def _handle_read(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(result_key=None)


async def _handle_v2_message_push(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(msg="", data="success")


async def _handle_v3_message_push_status(request: Request) -> Response:
    # EcoVacs Home
    userid = request.headers.get("userid", "")
    # token = request.headers.get("token", "")
    return response_success_v3(
        result_key=None,
        data={
            "uid": userid,
            "msgPushStatus": {"DEVICE": True, "SHARE": True},
            "devices": [
                {
                    "did": bot.did,
                    "msgPushStatus": True,
                    "nickName": bot.nick,
                }
                for bot in bot_repo.list_all()
            ],
        },
    )


async def _handle_v3_latest_by_did(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(data=[])


async def _handle_v3_message_list(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(data=[])


async def _handle_v3_product_msg_tabs(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(
        data=[
            {
                "code": "evt",
                "name": "Work messages",
            },
            {
                "code": "error",
                "name": "Malfunction messages",
            },
        ],
    )


async def _handle_v3_share_msg_has_unread_msg(_: Request) -> Response:
    # EcoVacs Home
    return response_success_v3(data={"count": 0, "unRead": False})
