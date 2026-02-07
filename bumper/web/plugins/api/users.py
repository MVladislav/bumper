"""Users plugin module."""

from collections.abc import Awaitable, Callable, Iterable, Mapping
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_service
from bumper.web.plugins import WebserverPlugin
from bumper.web.plugins.api.appsvr import create_device_list
from bumper.web.utils.response_helper import response_error_v6, response_success_v2

_LOGGER = logging.getLogger(__name__)


class UsersPlugin(WebserverPlugin):
    """Users plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/users/user.do", _handle_user),
        ]


HandlerFunction = Callable[[Mapping[str, Any], Request], Awaitable[Response | None]]


async def _handle_user(request: Request) -> Response:
    try:
        if request.content_type == "application/x-www-form-urlencoded":
            post_body = await request.post()
        else:
            post_body = json.loads(await request.text())

        todo: str = str(post_body.get("todo", ""))
        handler: HandlerFunction | None = _TODO_HANDLERS.get(todo)

        if handler is None:
            _LOGGER.warning(f"Unknown todo: {todo}")
            return response_error_v6(todo)

        try:
            response = await handler(post_body, request)
            if response is None:
                _LOGGER.warning(f"Known todo but failed to process: {todo}")
                return response_error_v6(todo)
            return response
        except Exception:
            _LOGGER.exception(f"Error while processing known todo: {todo}")
            return response_error_v6(todo)

    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling '_handle_user'"))
    raise HTTPInternalServerError


# ----------- Private Handlers -----------


async def _handle_find_best(post_body: Mapping[str, Any], _: Request) -> Response | None:
    service = post_body.get("service", "")
    if service == "EcoMsgNew":
        return web.json_response({"ip": bumper_isc.bumper_announce_ip, "port": bumper_isc.XMPP_LISTEN_PORT_TLS, "result": "ok"})
    if service == "EcoUpdate":
        return web.json_response(
            {"ip": bumper_isc.ECOVACS_UPDATE_SERVER, "port": bumper_isc.ECOVACS_UPDATE_SERVER_PORT, "result": "ok"},
        )
    return None


async def _handle_login_by_it_token(post_body: Mapping[str, Any], _: Request) -> Response | None:
    if "userId" in post_body:
        if token_repo.verify_it(post_body["userId"], post_body["token"]):
            return web.json_response(
                {
                    "resource": post_body["resource"],
                    "result": "ok",
                    "todo": "result",
                    "token": post_body["token"],
                    "userId": post_body["userId"],
                },
            )
    else:
        login_token = token_repo.login_by_it_token(post_body["token"])
        if login_token:
            return web.json_response(
                {
                    "resource": post_body["resource"],
                    "result": "ok",
                    "todo": "result",
                    "token": login_token.token,
                    "userId": login_token.userid,
                },
            )
    return None


async def _handle_get_auth_code(_: Mapping[str, Any], request: Request) -> Response | None:
    return await auth_service.get_auth_code_v2(request)


async def _handle_get_device_list(_: Mapping[str, Any], __: Request) -> Response | None:
    return web.json_response({"devices": create_device_list(), "result": "ok", "todo": "result"})


async def _handle_set_device_nick(post_body: Mapping[str, Any], _: Request) -> Response | None:
    if did := post_body.get("did"):
        bot_repo.set_nick(did, post_body.get("nick", ""))
        return response_success_v2(result_key="result")
    return None


async def _handle_add_one_device(post_body: Mapping[str, Any], _: Request) -> Response | None:
    if did := post_body.get("did"):
        bot_repo.set_nick(did, post_body.get("nick", ""))
        return response_success_v2(result_key="result")
    return None


async def _handle_delete_one_device(post_body: Mapping[str, Any], _: Request) -> Response | None:
    if did := post_body.get("did"):
        bot_repo.remove(did)
        return response_success_v2(result_key="result")
    return None


async def _handle_logout(post_body: Mapping[str, Any], __: Request) -> Response | None:
    user_id: str = post_body["userId"]
    user_repo.remove(user_id)
    client_repo.remove(user_id)
    return web.json_response({"todo": "result", "result": "ok"})


# ----------- Mapping -----------

_TODO_HANDLERS: dict[str, HandlerFunction] = {
    "FindBest": _handle_find_best,
    "loginByItToken": _handle_login_by_it_token,
    "GetAuthCode": _handle_get_auth_code,
    "GetDeviceList": _handle_get_device_list,
    "SetDeviceNick": _handle_set_device_nick,
    "AddOneDevice": _handle_add_one_device,
    "DeleteOneDevice": _handle_delete_one_device,
    "logout": _handle_logout,
}
