"""Users plugin module."""

from collections.abc import Mapping
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.db import bot_repo, client_repo, identity, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_service
from bumper.web.context import claimed_userid
from bumper.web.envelope import LEGACY_FLAT
from bumper.web.jwt import verify_jwt
from bumper.web.operations import Operation, dispatch
from bumper.web.payloads import device_list, user_info
from bumper.web.utils.models import BumperUser

from . import PREFIX

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


#: The operations of `user.do`. The shape of the answer belongs to the
#: operation, so the table names the shape every todo answers with.
USER_DO_OPERATIONS: dict[str, Operation] = {}


routes.post(f"{PREFIX}/users/user.do")(dispatch(USER_DO_OPERATIONS, LEGACY_FLAT))


async def _handle_find_best(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Announce the server the robot or the app has to talk to."""
    service = post_body.get("service", "")
    if service == "EcoMsgNew":
        return {"ip": bumper_isc.bumper_announce_ip, "port": bumper_isc.XMPP_LISTEN_PORT_TLS, "result": "ok"}
    if service == "EcoUpdate":
        return {
            "ip": bumper_isc.ECOVACS_UPDATE_SERVER,
            "port": bumper_isc.ECOVACS_UPDATE_SERVER_PORT,
            "result": "ok",
        }
    return None


async def _handle_login_by_it_token(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Log a client in with the token of the app."""
    token_str = post_body.get("token")
    if not isinstance(token_str, str) or not token_str:
        return None

    login_token = token_repo.login_by_it_token(token_str)
    if login_token is None:
        return None

    user = identity.resolve_user(
        post_body.get("userId"),
        token_user_id=login_token.userid,
    )
    owner = user_repo.get_by_id(login_token.userid)
    if user is None or owner is None or owner.userid != user.userid:
        return None

    user = identity.ensure_public_ids(user)
    presented = post_body.get("userId")
    if isinstance(presented, str) and presented:
        user = identity.adopt_public_id(user, presented)

    resource = post_body.get("resource")
    resource = resource if isinstance(resource, str) else ""
    realm = post_body.get("realm")
    realm = realm if isinstance(realm, str) else ""
    if resource:
        token_repo.set_client_for_it_token(token_str, resource=resource)
        client_repo.add("app", user.userid, realm, resource, device_id=login_token.device_id or "")

    return {
        "resource": resource,
        "result": "ok",
        "todo": "result",
        "token": login_token.token,
        "userId": user.iot_id,
        "last": auth_service.remaining_milliseconds(login_token),
    }


async def _handle_get_auth_code(request: Request, _: Mapping[str, Any]) -> Any:
    """Return the auth code of the user."""
    return {"code": await auth_service.get_auth_code_v2(request)}


async def _handle_get_device_list(request: Request, post_body: Mapping[str, Any]) -> Any:
    """Return the devices of the account."""
    return {"devices": device_list(_request_user(request, post_body))}


async def _handle_set_device_nick(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Rename a device."""
    if did := post_body.get("did"):
        bot_repo.set_nick(did, post_body.get("nick", ""))
    return None


async def _handle_add_one_device(request: Request, post_body: Mapping[str, Any]) -> Any:
    """Add a device to the shared inventory of local accounts."""
    did = post_body.get("did")
    if not isinstance(did, str) or not did:
        return None
    user = _request_user(request, post_body)
    if user is not None:
        identity.assign_bot_to_all_users(did)
    bot_repo.set_nick(did, post_body.get("nick", ""))
    return None


async def _handle_delete_one_device(request: Request, post_body: Mapping[str, Any]) -> Any:
    """Remove a device from the account."""
    did = post_body.get("did")
    if not isinstance(did, str) or not did:
        return None
    user = _request_user(request, post_body)
    if user is not None:
        user_repo.remove_bot(user.userid, did)
    return None


async def _handle_logout(request: Request, post_body: Mapping[str, Any]) -> Any:
    """Revoke the client of a logout without removing the account.

    The account keeps its devices, homes, and other clients. The token that
    names the client is revoked, and the client row it names is removed. A
    request that names no token can only be logged out as a whole.
    """
    user = _request_user(request, post_body)
    if user is None:
        return None

    auth = post_body.get("auth")
    token_str = auth.get("token") if isinstance(auth, Mapping) else None
    if isinstance(token_str, str) and token_str:
        token = token_repo.get_by_secret(token_str)
        if token is None:
            details = verify_jwt(token_str)
            auth_code = details.get("auth_code") if details is not None else None
            if isinstance(auth_code, str):
                token = token_repo.get_by_auth_code(auth_code)
        owner = user_repo.get_by_id(token.userid) if token is not None else None
        if token is None or owner is None or owner.userid != user.userid:
            return None
        token_repo.revoke_token(token.userid, token.token)
        if token.resource or token.client_id or token.device_id:
            client_repo.remove(
                owner.userid,
                resource=token.resource or None,
                client_id=token.client_id or None,
                device_id=token.device_id or None,
            )
        return None

    token_repo.revoke_all_for_user(user.userid)
    client_repo.remove(user.userid)
    return None


async def _handle_get_users_info(_: Request, post_body: Mapping[str, Any]) -> Any:
    """Return the members of the household."""
    requested = post_body.get("users")
    requested_ids = {str(user_id) for user_id in requested} if isinstance(requested, list) else set()

    users = []
    for user in user_repo.list_all():
        if requested_ids and not requested_ids.intersection(user.names):
            continue
        users.append(user_info(user))

    return {"users": users}


def _request_user(request: Request, post_body: Mapping[str, Any]) -> BumperUser | None:
    """Return the account a legacy request names."""
    auth = post_body.get("auth")
    user_id = post_body.get("userId") or post_body.get("userid")
    if not user_id and isinstance(auth, Mapping):
        user_id = auth.get("userid")
    if not user_id:
        user_id = claimed_userid(request)
    if isinstance(user_id, str) and user_id:
        return identity.resolve_user(user_id, prefer_device=True)
    return None


# ----------- Mapping -----------
USER_DO_OPERATIONS.update(
    {
        "FindBest": Operation(LEGACY_FLAT, _handle_find_best),
        "loginByItToken": Operation(LEGACY_FLAT, _handle_login_by_it_token),
        "GetAuthCode": Operation(LEGACY_FLAT, _handle_get_auth_code),
        "GetDeviceList": Operation(LEGACY_FLAT, _handle_get_device_list),
        "SetDeviceNick": Operation(LEGACY_FLAT, _handle_set_device_nick),
        "AddOneDevice": Operation(LEGACY_FLAT, _handle_add_one_device),
        "DeleteOneDevice": Operation(LEGACY_FLAT, _handle_delete_one_device),
        "logout": Operation(LEGACY_FLAT, _handle_logout),
        "GetUsersInfo": Operation(LEGACY_FLAT, _handle_get_users_info),
    },
)
