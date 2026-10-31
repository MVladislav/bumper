"""Auth util module."""

from collections.abc import Mapping
import datetime as dt
import json
import logging
from typing import Any
import uuid

import aiofiles
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
import jwt

from bumper.db import client_repo, identity, token_repo, user_repo
from bumper.utils import utils
from bumper.utils.account_ids import legacy_account_uid
from bumper.utils.account_key import decrypt_account_field
from bumper.utils.settings import config as bumper_isc
from bumper.web.context import read_body
from bumper.web.envelope import (
    ERR_TOKEN_INVALID,
    ERR_USER_DISABLE,
    ApiError,
)
from bumper.web.jwt import verify_jwt
from bumper.web.utils import models

_LOGGER = logging.getLogger(__name__)

GENERATE_AUTH_CODE_V1 = 1
GENERATE_AUTH_CODE_V2 = 2


async def login(request: Request) -> Any:
    """Answer a login or check-login request."""
    try:
        is_check_login = "checkLogin" in request.path
        device_id = request.match_info.get("devid")
        country_code = request.match_info.get("country", bumper_isc.ECOVACS_DEFAULT_COUNTRY)
        app_type = request.match_info.get("apptype") or ""

        if is_check_login:
            return _check_login(request, device_id, app_type, country_code)

        account = request.query.get("account")
        if not account:
            account = decrypt_account_field(request.query.get("encryptAccount", ""))
        if not account and request.method == "POST":
            body = await read_body(request)
            value = body.get("account")
            if isinstance(value, str):
                account = value
            if not account:
                encrypted = body.get("encryptAccount")
                account = decrypt_account_field(encrypted if isinstance(encrypted, str) else "")

        login_name = account or bumper_isc.USER_USERNAME_DEFAULT
        uid = request.query.get("uid")
        user = identity.resolve_login(login_name)
        if user is not None:
            if uid:
                user = identity.adopt_public_id(user, uid)
                user = identity.adopt_alias(user, uid)
            user = identity.ensure_public_ids(user)
        elif uid:
            user = identity.resolve_user(uid, device_id=device_id, prefer_device=device_id is not None)

        if user is None:
            email = login_name if _is_email(login_name) else None
            user = identity.create_account(login_name, email=email)

        _auth_any_user_extends(user, device_id)
        token = _generate_token(user.userid, device_id=device_id)
        return _get_login_details(app_type, country_code, user, token)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during login"))
    raise HTTPInternalServerError


def _check_login(request: Request, device_id: str | None, app_type: str, country_code: str) -> Any:
    """Check a session and keep the token the client already holds."""
    uid = request.query.get("uid")
    access_token = request.query.get("accessToken")
    user = identity.resolve_user(uid, device_id=device_id, prefer_device=device_id is not None)
    if user is None:
        _LOGGER.warning("No account found for the login request")
        msg = "Parameter error. Please try again later."
        raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)

    user = identity.ensure_public_ids(user)
    if uid:
        user = identity.adopt_public_id(user, uid)

    if access_token:
        if not _verify_access_token(user, access_token):
            msg = "Parameter error. Please try again later."
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)
        token = access_token
    else:
        token = _generate_token(user.userid, device_id=device_id)
    return _get_login_details(app_type, country_code, user, token)


def _auth_any_user_extends(user: models.BumperUser, device_id: str | None) -> None:
    """Bind the app installation to the account and drop lapsed tokens."""
    if device_id:
        user_repo.bind_device(user.userid, device_id)
    token_repo.revoke_user_expired(user.userid)


async def get_auth_code(request: Request) -> Any:
    """Return the IT token the app exchanges for an auth code."""
    try:
        user_id = request.query.get("uid")
        device_id = request.match_info.get("devid") or request.query.get("deviceId")
        user = identity.resolve_user(user_id, device_id=device_id, prefer_device=device_id is not None)
        if user is None:
            _LOGGER.warning(f"No user found for {user_id} (get_auth_code)")
            msg = f"No user found for {user_id}"
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)

        user = identity.ensure_public_ids(user)
        if user_id:
            user = identity.adopt_public_id(user, user_id)

        access_token = request.query.get("accessToken")
        if not access_token or not _verify_access_token(user, access_token):
            _LOGGER.warning("Get auth code failed, the access token is not valid")
            msg = "Expired user login"
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)

        token = _token_for_access_token(user, access_token)
        if token is not None and (it_token := _generate_it_token(user.userid, token.token)) is not None:
            return {"authCode": it_token, "ecovacsUid": user.uc_uid or user.account_id}

        _LOGGER.warning(f"Expired user login {user_id}")
        msg = "Expired user login"
        raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_auth_code'"))
    raise HTTPInternalServerError


def _verify_access_token(user: models.BumperUser, token: str) -> bool:
    """Return whether a token names this account."""
    row = token_repo.get_valid_by_token(token)
    if row is not None and _row_belongs_to(row, user):
        return True
    details = verify_jwt(token)
    if details is None:
        return False
    token_user = details.get("user_id")
    if not isinstance(token_user, str):
        return False
    resolved = user_repo.get_by_id(token_user)
    return resolved is not None and resolved.userid == user.userid


def _row_belongs_to(row: models.Token, user: models.BumperUser) -> bool:
    """Return whether a token row was issued for the account."""
    owner = user_repo.get_by_id(row.userid)
    return owner is not None and owner.userid == user.userid


def _token_for_access_token(user: models.BumperUser, token_str: str) -> models.Token | None:
    """Return the token row the presented access token names.

    The token can be the opaque portal token of a client, or a JWT whose
    claims name the client and the auth code. The row of another client is
    never used, so an IT token is attached to the client that asked for it.
    """
    row = token_repo.get_by_token(token_str)
    if row is not None and _row_belongs_to(row, user) and remaining_milliseconds(row) > 0:
        return row

    details = verify_jwt(token_str)
    if details is None:
        return None
    client_id = details.get("client_id")
    if isinstance(client_id, str):
        row = token_repo.get_by_client_id(client_id)
        if row is not None and _row_belongs_to(row, user) and remaining_milliseconds(row) > 0:
            return row
    auth_code = details.get("auth_code")
    if isinstance(auth_code, str):
        row = token_repo.get_by_auth_code(auth_code)
        if row is not None and _row_belongs_to(row, user) and remaining_milliseconds(row) > 0:
            return row
    return None


def _generate_it_token(user_id: str, portal_token: str | None = None) -> str | None:
    """Generate an IT token and attach it to the token row of the client."""
    new_it_token = f"GLOBAL_APP_ECOVACS_IOT_{uuid.uuid4().hex}"
    attached = token_repo.add_it_token_to_token(portal_token, new_it_token) if portal_token else False
    if attached or token_repo.add_it_token(user_id, new_it_token):
        return new_it_token
    _LOGGER.warning("Failed to create it_token")
    return None


def _ensure_token(user_id: str) -> models.Token | None:
    """Return the user's token, provisioning one if it was reaped.

    Auth codes attach to an existing token row, so a lapsed row would break
    the handshake until the user logs in again.
    """
    if (token := token_repo.get_first(user_id)) is not None:
        return token
    _LOGGER.info(f"No active token for {user_id}, provisioning a new one")
    _generate_token(user_id)
    return token_repo.get_first(user_id)


def issue_portal_token(user_id: str) -> models.Token | None:
    """Return a live portal token for an account, provisioning one if needed."""
    token_repo.revoke_user_expired(user_id)
    return _ensure_token(user_id)


def remaining_milliseconds(token: models.Token) -> int:
    """Return how long a token is still valid, in milliseconds."""
    now = dt.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)
    expiration = token.expiration
    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=bumper_isc.LOCAL_TIMEZONE)
    return max(0, int((expiration - now).total_seconds() * 1000))


async def get_new_auth(request: Request) -> Any:
    """Exchange an IT token for the auth code used by the robot transports."""
    try:
        post_body = await read_body(request)
        it_token: str | None = post_body.get("itToken")

        if it_token is None:
            _LOGGER.warning("New auth failed, 'itToken' not provided")
            msg = "New auth failed, 'itToken' not provided"
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)
        if (token := token_repo.login_by_it_token(it_token)) is None:
            _LOGGER.warning("New auth failed, no token found for it-token")
            msg = "New auth failed, no token found for it-token"
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)

        user = identity.resolve_user(token.userid)
        if user is None:
            msg = "New auth failed, no account found for it-token"
            raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)
        user = identity.ensure_public_ids(user)

        client_id = post_body.get("clientID")
        resource = post_body.get("resource")
        client_id = client_id if isinstance(client_id, str) else ""
        resource = resource if isinstance(resource, str) else ""
        if client_id or resource:
            token_repo.set_client_for_it_token(
                it_token,
                client_id=client_id or None,
                resource=resource or None,
            )
            client_repo.add(
                client_id or "app",
                user.userid,
                str(post_body.get("realm") or ""),
                resource,
                client_id=client_id,
                device_id=token.device_id or "",
            )

        token_repo.revoke_user_expired(user.userid)

        if token.auth_code:
            return token.auth_code
        if (auth_code := _generate_auth_code(user.userid, it_token)) is not None:
            return auth_code

        _LOGGER.warning(f"Expired client login {token.userid}")
        msg = "Expired client login"
        raise ApiError(msg=msg, code=ERR_TOKEN_INVALID)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_new_auth'"))
    raise HTTPInternalServerError


async def get_auth_code_v2(request: Request) -> Any:
    """Return the auth code carried by a legacy user request."""
    try:
        post_body = await read_body(request)
        auth = post_body.get("auth")
        user_id: str | None = None
        token_user_id: str | None = None
        auth_token: str | None = None
        if isinstance(auth, Mapping):
            user_id = auth.get("userid")
            value = auth.get("token")
            if isinstance(value, str):
                auth_token = value
                details = verify_jwt(auth_token)
                if details is not None and isinstance(details.get("user_id"), str):
                    token_user_id = details["user_id"]
        if user_id is None:
            user_id = request.query.get("u")

        device_id = request.match_info.get("devid") or request.query.get("deviceId") or post_body.get("deviceId")
        user = identity.resolve_user(
            user_id,
            device_id=device_id,
            token_user_id=token_user_id,
            prefer_device=device_id is not None,
        )
        if user is None:
            _LOGGER.warning(f"No user found for {user_id} (get_auth_code_v2)")
            msg = f"No user found for {user_id}"
            raise ApiError(msg=msg, code=ERR_USER_DISABLE)
        user = identity.ensure_public_ids(user)

        token_repo.revoke_user_expired(user.userid)
        token = _token_for_legacy_request(user, auth_token)
        if token is None:
            portal_token = _generate_token(user.userid)
            token = token_repo.get_by_token(portal_token)

        if token is not None and token.auth_code is not None:
            return token.auth_code
        if (
            token is not None
            and (auth_code := _generate_auth_code(user.userid, token.it_token, portal_token=token.token)) is not None
        ):
            return auth_code

        _LOGGER.warning(f"Auth error for {user_id}")
        msg = "Auth error"
        raise ApiError(msg=msg, code=ERR_USER_DISABLE)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'get_auth_code_v2'"))
    raise HTTPInternalServerError


def _token_for_legacy_request(user: models.BumperUser, auth_token: str | None) -> models.Token | None:
    """Return the token row a legacy request names.

    A request without a token can use the first row of the account. A request
    that names a token which is not a live secret of the account gets a new
    row, so the answer is never written onto another client's row.
    """
    if not auth_token:
        return token_repo.get_first(user.userid)

    if (token := token_repo.get_by_secret(auth_token)) is not None and _row_belongs_to(token, user):
        return token
    details = verify_jwt(auth_token)
    if details is None:
        return None
    client_id = details.get("client_id")
    if isinstance(client_id, str):
        token = token_repo.get_by_client_id(client_id)
        if token is not None and _row_belongs_to(token, user):
            return token
    auth_code = details.get("auth_code")
    if isinstance(auth_code, str):
        token = token_repo.get_by_auth_code(auth_code)
        if token is not None and _row_belongs_to(token, user):
            return token
    return None


async def oauth_callback(request: Request) -> Any:
    """Exchange an auth code for an access and refresh token."""
    try:
        if (auth_code := _get_auth_code(request)) is None:
            msg = "You not provide a auth_code"
            raise ApiError(msg=msg)
        if (token := token_repo.get_by_auth_code(auth_code)) is None:
            msg = "Auth code not known"
            raise ApiError(msg=msg)

        user = identity.resolve_user(token.userid)
        if user is None:
            msg = "No account found for auth code"
            raise ApiError(msg=msg)
        user = identity.ensure_public_ids(user)

        client_id = token.client_id or _client_id_from_request(request)
        client = client_repo.get_by_client_id(client_id) if client_id else None
        if client is None:
            client = client_repo.get(user.userid)
        resource = token.resource or (client.resource if client is not None else None)
        if client_id and resource:
            client_repo.add(
                client_id,
                user.userid,
                client.realm if client is not None else "",
                resource,
                client_id=client_id,
                device_id=token.device_id or "",
            )

        claims = {
            "c": client_id,
            "u": user.iot_id,
            "r": resource,
            "ac": auth_code,
        }

        access_token, access_expires_at = await generate_jwt_helper(
            data=claims,
            t="a",
            exp_seconds=bumper_isc.ACCESS_TOKEN_VALIDITY_SECONDS,
        )
        refresh_token, refresh_expires_at = await generate_jwt_helper(
            data=claims,
            t="r",
            exp_seconds=bumper_isc.REFRESH_TOKEN_VALIDITY_SECONDS,
        )
        token_repo.extend_oauth_session(
            auth_code,
            dt.datetime.fromtimestamp(refresh_expires_at, tz=bumper_isc.LOCAL_TIMEZONE),
        )
        return {
            "userId": user.iot_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expire_at": access_expires_at * 1000,
        }

    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during 'oauth_callback'"))
    raise HTTPInternalServerError


def _client_id_from_request(request: Request) -> str | None:
    """Return the app client id carried by an OAuth request."""
    state = request.query.get("state")
    if state:
        try:
            parsed = json.loads(state)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            cid = parsed.get("cid")
            if isinstance(cid, str) and cid:
                return cid
    cid = request.query.get("cid") or request.query.get("client_id")
    return cid or None


def _get_auth_code(request: Request) -> str | None:
    """Return the auth code from the query or the refresh token."""
    auth_code = request.query.get("code")
    if auth_code is not None:
        return auth_code

    refresh_token = request.query.get("refresh_token")
    if refresh_token is None:
        return None
    if (jwt_details := verify_jwt(refresh_token, token_type="r")) is None:  # noqa: S106
        return None
    return jwt_details.get("auth_code")


def _check_token(apptype: str, country_code: str, user: models.BumperUser, token_str: str) -> tuple[bool, Any]:
    """Return whether a token belongs to the user and the login document if it does."""
    if token_repo.verify(user.userid, token_str):
        return (True, _get_login_details(apptype, country_code, user, token_str))
    msg = "Parameter error. Please try again later."
    return (False, ApiError(msg=msg, code=ERR_TOKEN_INVALID))


def _get_login_details(apptype: str, country_code: str, user: models.BumperUser, token: str) -> dict[str, Any]:
    """Build the login document for a user and token."""
    login_name = user.login_name or user.username
    details: dict[str, Any] = {
        "accessToken": token,
        "email": user.email or bumper_isc.USER_MAIL_DEFAULT,
        "isNew": None,
        "loginName": login_name,
        "mobile": None,
        "ucUid": user.uc_uid or user.account_id,
        "uid": user.account_id,
        "username": user.username,
        "country": country_code,
        "verifyDevice": "N",
    }

    if "global_" in apptype:
        details.update({"loginName": login_name, "mobile": None})

    return details


def _is_email(value: str) -> bool:
    """Return whether a login name looks like an email address."""
    local, _, domain = value.partition("@")
    return bool(local and domain and "." in domain)


def _generate_uid(account: str | None) -> str:
    """Return the account id older Bumper versions derived from a login name."""
    return legacy_account_uid(account or bumper_isc.USER_USERNAME_DEFAULT)


def _generate_token(
    user_id: str,
    *,
    device_id: str | None = None,
    client_id: str | None = None,
    resource: str | None = None,
) -> str:
    """Create an access token and store it for the client."""
    token = uuid.uuid4().hex
    token_repo.add(user_id, token, client_id=client_id, resource=resource, device_id=device_id)
    return token


def _generate_auth_code(user_id: str, it_token: str | None = None, *, portal_token: str | None = None) -> str | None:
    """Generate an auth code and attach it to the client's token row."""
    new_auth_code = uuid.uuid4().hex
    attached = token_repo.add_auth_code_for_it_token(it_token, new_auth_code) if it_token else False
    if not attached and portal_token:
        attached = token_repo.add_auth_code_to_token(portal_token, new_auth_code)
    if attached or token_repo.add_auth_code(user_id, new_auth_code):
        return new_auth_code
    _LOGGER.warning("Failed to create auth_code")
    return None


async def generate_jwt_helper(
    data: dict[str, Any] | None = None,
    t: str = "r",
    exp_seconds: int = bumper_isc.ACCESS_TOKEN_VALIDITY_SECONDS,
    algorithm: str = bumper_isc.TOKEN_JWT_ALG,
) -> tuple[str, int]:
    """Sign a JWT with the TLS server key."""
    if data is None:
        data = {}
    now_dt = dt.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)
    exp_dt = now_dt + dt.timedelta(seconds=int(exp_seconds))

    headers = {
        "alg": algorithm,
        "typ": "JWT",
    }
    payload = {
        "t": t,
        "iat": int(now_dt.timestamp()),
        "exp": int(exp_dt.timestamp()),
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
