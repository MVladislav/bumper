"""Auth util module."""

import datetime
import hashlib
import json
import logging
from typing import Any
import uuid

import aiofiles
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import jwt

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.utils import models
from bumper.web.utils.response_helper import (
    ERR_TOKEN_INVALID,
    ERR_USER_DISABLE,
    response_error_v1,
    response_error_v2,
    response_error_v4,
    response_error_v9,
    response_success_v1,
    response_success_v2,
    response_success_v3,
)

_LOGGER = logging.getLogger(__name__)

GENERATE_AUTH_CODE_V1 = 1
GENERATE_AUTH_CODE_V2 = 2

# ******************************************************************************
#
# LOGIN UTILS
#
# ******************************************************************************


async def login(request: Request) -> Response:
    """Perform login."""
    try:
        uid: str | None = None
        access_token: str | None = None
        check = False
        if "checkLogin" in request.path:
            uid = request.query.get("uid")
            access_token = request.query.get("accessToken")
            check = True
        else:
            uid = _generate_uid(request.query.get("account"))
            if uid is None or uid == "":
                uid = _generate_uid(request.query.get("encryptAccount"))
            if uid is None or uid == "":
                uid = _generate_uid(request.query.get("authAppkey"))
            _ = request.query.get("encryptPwd")
            check = False

        device_id = request.match_info.get("devid")
        country_code = request.match_info.get("country", bumper_isc.ECOVACS_DEFAULT_COUNTRY)
        app_type = request.match_info.get("apptype")

        if bumper_isc.USE_AUTH:
            _LOGGER.info(f"Client with devid {device_id} attempting login")
            if device_id is not None and app_type is not None:
                # Performing basic "auth" using devid, super insecure
                user = user_repo.get_by_device_id(device_id)
                if user is None:
                    _LOGGER.warning(f"No user found for {device_id} (login)")
                else:
                    if "checkLogin" in request.path:
                        return _check_token(app_type, country_code, user, request.query.get("accessToken", ""))[1]
                    # Deactivate old tokens and authcodes
                    token_repo.revoke_user_expired(user.userid)
                    return response_success_v1(_get_login_details(app_type, country_code, user, _generate_token(user.userid)))
            return response_error_v1(msg="Parameter error. Please try again later.", code=ERR_TOKEN_INVALID)

        if device_id is not None and app_type is not None:
            return _auth_any(uid, access_token, device_id, app_type, country_code, check)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during login"))
    raise HTTPInternalServerError


def _auth_any(
    uid: str | None,
    token_str: str | None,
    device_id: str,
    app_type: str,
    country_code: str,
    check: bool,
) -> Response:
    """Authenticate user or validate existing session.

    Login (!check): Always generates fresh token.
    CheckLogin (check): Validates existing token or generates new one.
    """
    # Ensure valid UID
    uid = uid or _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)
    # Ensure user exists
    user = user_repo.get_by_id(uid)
    if user is None:
        user_repo.add(uid)
        user = user_repo.get_by_id(uid)

    if user is None:
        return response_error_v1(msg="Parameter error. Please try again later.", code=ERR_TOKEN_INVALID)

    # Update user context and cleanup old tokens
    _auth_any_user_extends(user, device_id)

    # Determine token strategy
    is_check_login = check and token_str is not None
    if not is_check_login or (token_str and not token_repo.get(user.userid, token_str)):
        token_str = _generate_token(user.userid)
    if token_str is None:
        token_str = _generate_token(user.userid)

    # Build primary success response
    body = response_success_v1(_get_login_details(app_type, country_code, user, token_str))

    # For check-login, validate original token and use its response if valid
    if is_check_login:
        success, result = _check_token(app_type, country_code, user, token_str)
        if success is True:  # We ignore when token check fails ;) and only use other result when not False
            body = result

    return body


def _auth_any_user_extends(user: models.BumperUser, device_id: str) -> None:
    # Add current used device to user
    user_repo.add_device(user.userid, device_id)
    # Add all known bots to the user
    for bot in bot_repo.list_all():
        if bot.did is not None and bot.did != "":
            user_repo.add_bot(user.userid, bot.did)
        else:
            _LOGGER.error(f"Bot has not a DID assigned :: {bot.as_dict()}")

    # Deactivate old tokens and auth_codes
    token_repo.revoke_user_expired(user.userid)


# ******************************************************************************
#
# AUTH UTILS :: IT Token
#
# ******************************************************************************


async def get_auth_code(request: Request) -> Response:
    """Get auth code."""
    try:
        user_id = request.query.get("uid")
        # access_token = request.query.get("accessToken")

        user: models.BumperUser | None = None
        if user_id is not None:
            user = user_repo.get_by_id(user_id)
        if user is None:
            user = _fallback_user_by_device_id(request)
        if user is None:
            _LOGGER.warning(f"No user found for {user_id} (get_auth_code)")
            return response_error_v9(msg=f"No user found for {user_id}", code=ERR_TOKEN_INVALID)

        if (auth_code := _generate_it_token(user.userid)) is not None:
            return response_success_v1(
                {
                    "authCode": auth_code,
                    "ecovacsUid": user.userid,  # TODO: change, this is not my userid | ucid | ucuid
                },
            )

        _LOGGER.warning(f"Expired user login {user_id}")
        return response_error_v9(msg="Expired user login", code=ERR_TOKEN_INVALID)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_auth_code'"))
    raise HTTPInternalServerError


def _fallback_user_by_device_id(request: Request) -> models.BumperUser | None:
    device_id = request.match_info.get("devid")  # Ecovacs
    if device_id is None:
        device_id = request.query.get("deviceId")  # Ecovacs Home
    if device_id is not None:
        return user_repo.get_by_device_id(device_id)
    return None


def _generate_it_token(user_id: str) -> str | None:
    """Generate it token."""
    # Generate new it_token and update to existing token entry
    new_it_token = f"GLOBAL_APP_ECOVACS_IOT_{uuid.uuid4().hex}"
    if token_repo.add_it_token(user_id, new_it_token):
        return new_it_token
    _LOGGER.warning("Failed to create it_token")
    return None


# ******************************************************************************
#
# AUTH UTILS :: New Auth
#
# ******************************************************************************


async def get_new_auth(request: Request) -> Response:
    """Get new auth do."""
    try:
        post_body = json.loads(await request.text())
        it_token: str | None = post_body.get("itToken")  # NOTE: created with `/v1/global/auth/getAuthCode`

        if it_token is None:
            _LOGGER.warning("New auth failed, 'itToken' not provided")
            return response_error_v2(msg="New auth failed, 'itToken' not provided", code=ERR_TOKEN_INVALID)
        if (token := token_repo.login_by_it_token(it_token)) is None:
            _LOGGER.warning("New auth failed, no token found for it-token")
            return response_error_v2(msg="New auth failed, no token found for it-token", code=ERR_TOKEN_INVALID)

        token_repo.revoke_user_expired(token.userid)

        auth_code: str | None = None
        if token.auth_code and (auth_code := token.auth_code) is not None:
            return response_success_v2(data=auth_code, data_key="authCode", code=None, result_key="result")
        if (auth_code := _generate_auth_code(token.userid)) is not None:
            return response_success_v2(data=auth_code, data_key="authCode", code=None, result_key="result")

        _LOGGER.warning(f"Expired client login {token.userid}")
        return response_error_v2(msg="Expired client login", code=ERR_TOKEN_INVALID)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_new_auth'"))
    raise HTTPInternalServerError


# ******************************************************************************
#
# AUTH UTILS :: ...
#
# ******************************************************************************


async def get_auth_code_v2(request: Request) -> Response:
    """Get auth code v2."""
    try:
        post_body = json.loads(await request.text())
        user_id = post_body.get("auth", {}).get("userid")
        # access_token = post_body.get("auth", {}).get("token")

        user: models.BumperUser | None = None
        if user_id is not None:
            user = user_repo.get_by_id(user_id)
        if user is None:
            _LOGGER.warning(f"No user found for {user_id} (get_auth_code_v2)")
            return response_error_v2(msg=f"No user found for {user_id}", code=ERR_USER_DISABLE)

        token_repo.revoke_user_expired(user_id)
        token = token_repo.get_first(user_id)

        if (token and (auth_code := token.auth_code)) is not None:
            return response_success_v2(data=auth_code, data_key="code", code=None, result_key="result")
        if (auth_code := _generate_auth_code(user.userid)) is not None:
            return response_success_v2(data=auth_code, data_key="code", code=None, result_key="result")

        _LOGGER.warning(f"Auth error for {user_id}")
        return response_error_v2(msg="Auth error", code=ERR_USER_DISABLE)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_auth_code_v2'"))
    raise HTTPInternalServerError


# ******************************************************************************
#
# OAUTH UTILS
#
# ******************************************************************************


async def oauth_callback(request: Request) -> Response:
    """Oauth callback."""
    try:
        if (auth_code := _get_auth_code(request)) is None:
            return response_error_v4(msg="You not provide a auth_code")
        if (token := token_repo.get_by_auth_code(auth_code)) is None:
            return response_error_v4(msg="Auth code not known")

        client = client_repo.get(token.userid)

        client_id = client.userid if client is not None else None
        client_resource = client.resource if client is not None else None

        access_token, _ = await generate_jwt_helper(
            data={
                "c": client_id,
                "u": token.userid,
                "r": client_resource,
                "ac": auth_code,
            },
            t="a",
        )
        refresh_token, expire_at = await generate_jwt_helper(
            data={
                "c": client_id,
                "u": token.userid,
                "r": client_resource,
                "ac": auth_code,
            },
            t="r",
        )
        return response_success_v3(
            data={
                "userId": token.userid,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expire_at": expire_at,
            },
        )

    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'oauth_callback'"))
    raise HTTPInternalServerError


def _get_auth_code(request: Request) -> str | None:
    """Get auth code."""
    auth_code = request.query.get("code")
    if auth_code is not None:
        return auth_code

    refresh_token = request.query.get("refresh_token")
    if refresh_token is None:
        return None
    if (jwt_details := _extract_jwt_details(refresh_token)) is None:
        return None
    return jwt_details.get("auth_code")


# ******************************************************************************
#
# HELPER UTILS
#
# ******************************************************************************


def _check_token(apptype: str, country_code: str, user: models.BumperUser, token_str: str) -> tuple[bool, Response]:
    if token_repo.verify(user.userid, token_str):
        return (True, response_success_v1(_get_login_details(apptype, country_code, user, token_str)))
    return (False, response_error_v1(msg="Parameter error. Please try again later.", code=ERR_TOKEN_INVALID))


def _get_login_details(apptype: str, country_code: str, user: models.BumperUser, token: str) -> dict[str, Any]:
    details: dict[str, Any] = {
        "accessToken": token,
        "email": bumper_isc.USER_MAIL_DEFAULT,
        "isNew": None,
        "loginName": user.userid,
        "mobile": None,
        "ucUid": user.userid,
        "uid": user.userid,
        "username": user.username,
        "country": country_code,
        "verifyDevice": "N",
    }

    if "global_" in apptype:
        details.update({"ucUid": details["uid"], "loginName": details["username"], "mobile": None})

    return details


def _generate_uid(account: str | None) -> str:
    """Generate an uid from a given account name."""
    if account is None:
        account = bumper_isc.USER_USERNAME_DEFAULT
    hash_object = hashlib.sha256()
    hash_object.update(account.encode("utf-8"))
    return hash_object.hexdigest()[:20]


def _generate_token(user_id: str) -> str:
    """Generate new token and add to DB."""
    token = uuid.uuid4().hex
    token_repo.add(user_id, token)
    return token


def _generate_auth_code(user_id: str) -> str | None:
    """Generate auth code."""
    # Generate new auth_code and update to existing token entry
    new_auth_code = uuid.uuid4().hex
    if token_repo.add_auth_code(user_id, new_auth_code):
        return new_auth_code
    _LOGGER.warning("Failed to create auth_code")
    return None


async def generate_jwt_helper(
    data: dict[str, Any] | None = None,
    t: str = "r",
    exp_seconds: int = bumper_isc.TOKEN_VALIDITY_SECONDS,
    algorithm: str = bumper_isc.TOKEN_JWT_ALG,
) -> tuple[str, int]:
    """Generate JWT."""
    if data is None:
        data = {}
    now_dt = datetime.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)
    exp_dt = now_dt + datetime.timedelta(seconds=int(exp_seconds))

    headers = {
        "alg": algorithm,
        "typ": "JWT",
    }
    payload = {
        "t": t,
        "iat": int(now_dt.timestamp()),
        "exp": int(exp_dt.timestamp()) if t != "a" else int(now_dt.timestamp()),
    }
    if data:
        payload.update(data)

    async with aiofiles.open(bumper_isc.server_key) as cert_file:
        private_key = await cert_file.read()

    return (
        jwt.encode(
            payload,
            private_key,
            algorithm=algorithm,
            headers=headers,
        ),
        int(exp_dt.timestamp()),
    )


def get_jwt_details(auth_header: str | None) -> dict[str, Any] | None:
    """Extract JWT helper."""
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ")[1]
    return _extract_jwt_details(token)


def _extract_jwt_details(token: str | None) -> dict[str, Any] | None:
    if token is None:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return {
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp"),
            "client_id": payload.get("c"),
            "user_id": payload.get("u"),
            "client_resource": payload.get("r"),
            "auth_code": payload.get("ac"),
        }
    except jwt.DecodeError:
        return None
