"""Neng plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.db import bot_repo
from bumper.web.envelope import LEGACY, LEGACY_BARE, LEGACY_NO_RET, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/neng/message/hasUnreadMsg")
@bind(LEGACY_BARE)
async def _handle_has_unread_message(_: Request) -> Any:
    # EcoVacs Home
    return {"hasUnRead": False, "shareMsgUnRead": False}


@routes.view(f"{PREFIX}/neng/message/getShareMsgs")
@bind(LEGACY_BARE)
async def _handle_get_share_msgs(_: Request) -> Any:
    # EcoVacs Home
    return {"hasNext": False, "msgs": []}


@routes.view(f"{PREFIX}/neng/message/getlist")
@bind(LEGACY_BARE)
async def _handle_get_list(_: Request) -> Any:
    # EcoVacs Home
    return {"hasNext": False, "msgs": []}


@routes.view(f"{PREFIX}/neng/message/read")
@bind(LEGACY_NO_RET.with_optional_data())
async def _handle_read(_: Request) -> Any:
    # EcoVacs Home
    return None


@routes.view(f"{PREFIX}/neng/v2/message/push")
@bind(LEGACY.with_result(None).with_msg(("message", "")))
async def _handle_v2_message_push(_: Request) -> Any:
    # EcoVacs Home
    return "success"


@routes.view(f"{PREFIX}/neng/v3/message/pushStatus")
@bind(LEGACY.with_result(None))
async def _handle_v3_message_push_status(request: Request) -> Any:
    # EcoVacs Home
    userid = request.headers.get("userid", "")
    return {
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
    }


@routes.view(f"{PREFIX}/neng/v3/message/latest_by_did")
@bind(LEGACY_NO_RET)
async def _handle_v3_latest_by_did(_: Request) -> Any:
    # EcoVacs Home
    return []


@routes.view(f"{PREFIX}/neng/v3/message/list")
@bind(LEGACY)
async def _handle_v3_message_list(_: Request) -> Any:
    # EcoVacs Home
    return []


@routes.view(f"{PREFIX}/neng/v3/product/msg/tabs")
@bind(LEGACY)
async def _handle_v3_product_msg_tabs(_: Request) -> Any:
    # EcoVacs Home
    return [
        {
            "code": "evt",
            "name": "Work messages",
        },
        {
            "code": "error",
            "name": "Malfunction messages",
        },
    ]


@routes.view(f"{PREFIX}/neng/v3/shareMsg/read")
@bind(LEGACY_NO_RET.with_optional_data())
async def _handle_read_share_message(_: Request) -> Any:
    """Read a shared message."""
    return None


@routes.view(f"{PREFIX}/neng/v3/shareMsg/hasUnreadMsg")
@bind(LEGACY_NO_RET)
async def _handle_v3_share_msg_has_unread_msg(_: Request) -> Any:
    # EcoVacs Home
    return {"count": 0, "unRead": False}
