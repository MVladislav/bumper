import asyncio
import base64
from datetime import datetime
import json
import logging
from types import CoroutineType
from typing import Any

from aiohttp.test_utils import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
import jwt
import pytest

from bumper.db import client_repo, token_repo, user_repo
from bumper.utils.account_ids import is_account_uid
from bumper.utils.account_key import account_public_key
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import (
    _check_token,
    _generate_auth_code,
    _generate_token,
    _generate_uid,
    _get_login_details,
    generate_jwt_helper,
)
from bumper.web.envelope import ApiError
from bumper.web.jwt import get_jwt_details, verify_jwt
from bumper.web.utils import models


def _encrypt_account(value: str) -> str:
    """Encrypt a login name the way the app does."""
    key = serialization.load_der_public_key(base64.b64decode(account_public_key()))
    ciphertext = key.encrypt(value.encode(), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("ascii")


# --- Tests for newauth.do ---
@pytest.mark.usefixtures("clean_database")
async def test_get_new_auth_valid(webserver_client: TestClient) -> None:
    """The IT token is exchanged for an auth code and the client is recorded."""
    user = user_repo.create("newauth_user")
    token_repo.add(user.userid, "portal_token")
    token_repo.add_it_token(user.userid, "valid_it_token")

    payload = {
        "itToken": "valid_it_token",
        "todo": "OLoginByITToken",
        "clientID": "client_new",
        "resource": "RES_NEW",
    }
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data.get("result") == "ok"
    assert data.get("authCode")
    stored = token_repo.get_by_it_token("valid_it_token")
    assert stored is not None
    assert stored.client_id == "client_new"
    assert stored.resource == "RES_NEW"
    assert client_repo.get_by_client_id("client_new").userid == user.userid


@pytest.mark.usefixtures("clean_database")
async def test_get_existing_auth_valid(webserver_client: TestClient) -> None:
    """An auth code that a client already holds is returned unchanged."""
    user = user_repo.create("existing_auth_user")
    token_repo.add(user.userid, "portal_token")
    token_repo.add_it_token(user.userid, "valid_it_token")
    token_repo.add_auth_code(user.userid, "existingToken")

    payload = {"itToken": "valid_it_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data.get("result") == "ok"
    assert data.get("authCode") == "existingToken"


async def test_get_new_auth_missing_token(webserver_client: TestClient) -> None:
    payload = {"todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "New auth failed, 'itToken' not provided"


async def test_get_new_auth_invalid_token(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.token_repo.login_by_it_token", lambda _: None)
    payload = {"itToken": "invalid_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "New auth failed, no token found for it-token"


@pytest.mark.usefixtures("clean_database")
async def test_get_new_auth_generate_code_fails(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = user_repo.create("no_code_user")
    token_repo.add(user.userid, "portal_token")
    token_repo.add_it_token(user.userid, "some_token")
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda *_: None)

    payload = {"itToken": "some_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "Expired client login"


# --- Tests for getAuthCode ---
@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_valid(webserver_client: TestClient) -> None:
    """A live access token buys an IT token and the account's unified id."""
    user = user_repo.create("testuser")
    token_repo.add(user.userid, "access_token")

    async with webserver_client.get(
        f"/v1/global/auth/getAuthCode?uid={user.account_id}&accessToken=access_token",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["data"]["authCode"].startswith("GLOBAL_APP_ECOVACS_IOT_")
    assert data["data"]["ecovacsUid"] == user.uc_uid


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_user_not_found(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=missing&accessToken=token") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert data.get("msg").startswith("No user found")


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_token_fail(webserver_client: TestClient) -> None:
    """A login without a valid access token cannot name an IT token."""
    user = user_repo.create("no_access_token_user")

    async with webserver_client.get(f"/v1/global/auth/getAuthCode?uid={user.account_id}") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert not data.get("success")
        assert data.get("msg") == "Expired user login"


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_resolves_the_user_of_the_device(webserver_client: TestClient) -> None:
    user = user_repo.create("from_device")
    user_repo.bind_device(user.userid, "device123")
    token_repo.add(user.userid, "access_token")

    async with webserver_client.get(
        "/v1/global/auth/getAuthCode?deviceId=device123&accessToken=access_token",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["data"]["authCode"].startswith("GLOBAL_APP_ECOVACS_IOT_")
    assert data["data"]["ecovacsUid"] == user.uc_uid


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_accepts_a_signed_access_token(webserver_client: TestClient) -> None:
    user = user_repo.create("jwt_access_user")
    token_repo.add(user.userid, "portal_token", client_id="client_jwt", resource="RES_JWT")
    token_repo.add_auth_code(user.userid, "auth_jwt")
    access_token, _ = await generate_jwt_helper(
        data={"u": user.iot_id, "c": "client_jwt", "r": "RES_JWT", "ac": "auth_jwt"},
        t="a",
    )

    async with webserver_client.get(
        f"/v1/global/auth/getAuthCode?uid={user.account_id}&accessToken={access_token}",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["data"]["authCode"].startswith("GLOBAL_APP_ECOVACS_IOT_")
    stored = token_repo.get_by_it_token(data["data"]["authCode"])
    assert stored is not None
    assert stored.client_id == "client_jwt"


# --- Tests for get_auth_code_v2 ---
@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_v2_valid_user(webserver_client: TestClient) -> None:
    user = user_repo.create("testuser")
    token_repo.add(user.userid, "token")
    token_repo.add_auth_code(user.userid, "existing_auth_code")

    payload = {"todo": "GetAuthCode", "auth": {"userid": user.account_id}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data.get("result") == "ok"
    assert data.get("code") == "existing_auth_code"


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_v2_valid_user_no_token(webserver_client: TestClient) -> None:
    user = user_repo.create("testuser")

    payload = {"todo": "GetAuthCode", "auth": {"userid": user.account_id}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data.get("result") == "ok"
    assert data.get("code")
    assert token_repo.get_by_auth_code(data["code"]) is not None


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_v2_user_not_found(webserver_client: TestClient) -> None:
    payload = {"todo": "GetAuthCode", "auth": {"userid": "nonexistent"}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("errno") == "1004"  # ERR_USER_DISABLE
        assert "No user found" in data.get("error")


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_v2_auth_error(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = user_repo.create("testuser")
    token_repo.add(user.userid, "token")
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda *_, **__: None)

    payload = {"todo": "GetAuthCode", "auth": {"userid": user.account_id}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("errno") == "1004"  # ERR_USER_DISABLE
        assert data.get("error") == "Auth error"


# --- Tests for oauth_callback ---
def _token_with_auth_code(auth_code: str) -> str:
    """Return a signed refresh token that carries an auth code."""
    now = int(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())
    return jwt.encode(
        {"ac": auth_code, "t": "r", "iat": now, "exp": now + 60},
        bumper_isc.server_key.read_text(encoding="utf-8"),
        algorithm=bumper_isc.TOKEN_JWT_ALG,
    )


@pytest.mark.usefixtures("clean_database")
async def test_oauth_callback_success(webserver_client: TestClient) -> None:
    """The auth code of a client buys tokens that name the account and the client."""
    user = user_repo.create("oauth_user")
    client_repo.add("app", user.userid, "ecouser.net", "RES_NEW", client_id="client_new")
    token_repo.add(user.userid, "portal_token", client_id="client_new", resource="RES_NEW")
    token_repo.add_auth_code(user.userid, "auth123")

    async with webserver_client.get(
        "/api/appsvr/oauth_callback",
        params={"code": "auth123", "state": json.dumps({"cid": "client_new"})},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["data"]["userId"] == user.iot_id
    assert data["data"]["access_token"]
    assert data["data"]["refresh_token"]
    details = verify_jwt(data["data"]["access_token"])
    assert details is not None
    assert details["user_id"] == user.iot_id
    assert details["client_id"] == "client_new"
    assert details["client_resource"] == "RES_NEW"
    refresh_details = verify_jwt(data["data"]["refresh_token"], token_type="r")  # noqa: S106
    assert refresh_details is not None
    session = token_repo.get_by_token("portal_token")
    assert session is not None
    assert int(session.expiration.timestamp()) == refresh_details["expires_at"]
    assert details["auth_code"] == "auth123"


@pytest.mark.usefixtures("clean_database")
async def test_oauth_session_survives_a_fifty_minute_app_idle(webserver_client: TestClient) -> None:
    """The refresh and portal sessions outlive the short access JWT."""
    user = user_repo.create("idle_session_user")
    user_repo.bind_device(user.userid, "idle_device")
    token_repo.add(user.userid, "portal_token", client_id="idle_client", resource="IDLE")
    token_repo.add_auth_code(user.userid, "idle_auth")

    async with webserver_client.get("/api/appsvr/oauth_callback?code=idle_auth") as resp:
        assert resp.status == 200
        result = await resp.json()

    access = verify_jwt(result["data"]["access_token"])
    refresh = verify_jwt(result["data"]["refresh_token"], token_type="r")  # noqa: S106
    assert access is not None
    assert refresh is not None
    assert access["expires_at"] - access["issued_at"] == 1800
    assert refresh["expires_at"] - refresh["issued_at"] == 30 * 24 * 60 * 60

    stored = token_repo.get_by_auth_code("idle_auth")
    assert stored is not None
    now = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)
    assert (stored.expiration - now).total_seconds() > 50 * 60

    async with webserver_client.get(
        f"/v1/private/us/en/idle_device/global_e/3.16.0/google_play/1/user/checkLogin?"
        f"uid={user.account_id}&accessToken=portal_token",
    ) as resp:
        check_login = await resp.json()
    assert check_login["code"] == "0000"


@pytest.mark.usefixtures("clean_database")
async def test_the_oauth_callback_answers_with_the_expiry_of_the_access_token(
    webserver_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The expiry belongs to the access token, not to the refresh token."""
    user = user_repo.create("oauth_expiry_user")
    token_repo.add(user.userid, "portal_token")
    token_repo.add_auth_code(user.userid, "auth123")

    async def dummy_generate_jwt(data: Any, t: str, **args: dict[str, Any]) -> CoroutineType[Any, Any, tuple[str, int]]:  # noqa: ARG001
        return f"{t}_token", 1000 if t == "a" else 2000

    monkeypatch.setattr("bumper.web.auth_service.generate_jwt_helper", dummy_generate_jwt)

    async with webserver_client.get("/api/appsvr/oauth_callback?code=auth123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["expire_at"] == 1000 * 1000


@pytest.mark.usefixtures("clean_database")
async def test_the_oauth_token_route_answers_with_the_tokens_of_the_refresh_token(
    webserver_client: TestClient,
) -> None:
    """The refresh grant answers with the same answer as the callback."""
    user = user_repo.create("oauth_refresh_user")
    client_repo.add("app", user.userid, "ecouser.net", "RES_NEW", client_id="client_new")
    token_repo.add(user.userid, "portal_token", client_id="client_new", resource="RES_NEW")
    token_repo.add_auth_code(user.userid, "auth123")

    refresh_token = _token_with_auth_code("auth123")
    async with webserver_client.get(
        f"/api/appsvr/oauth/token?grant_type=refresh_token&refresh_token={refresh_token}&client_id=client_new",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["ret"] == "ok"
    assert data["data"]["userId"] == user.iot_id
    details = verify_jwt(data["data"]["access_token"])
    assert details is not None
    assert details["user_id"] == user.iot_id
    assert details["client_id"] == "client_new"
    assert details["client_resource"] == "RES_NEW"
    refresh_details = verify_jwt(data["data"]["refresh_token"], token_type="r")  # noqa: S106
    assert refresh_details is not None
    session = token_repo.get_by_token("portal_token")
    assert session is not None
    assert int(session.expiration.timestamp()) == refresh_details["expires_at"]


async def test_the_oauth_token_route_answers_a_failure_in_its_shape(webserver_client: TestClient) -> None:
    """A failure of the oauth token route is an envelope, not a stack trace."""
    async with webserver_client.get("/api/appsvr/oauth/token?code=unknown") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["ret"] == "fail"
        assert data["error"] == "Auth code not known"


# --- Tests for _generate_auth_code ---
def test_generate_auth_code_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.token_repo.add_auth_code", lambda _, __: True)

    result = _generate_auth_code("testuser")
    assert result is not None


def test_generate_auth_code_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.token_repo.add_auth_code", lambda _, __: False)

    result = _generate_auth_code("testuser")
    assert result is None


# --- Tests for generate_jwt_helper ---
@pytest.mark.asyncio
async def test_generate_jwt_helper_success() -> None:
    token, exp = await generate_jwt_helper(data={"test": "data"}, t="a", exp_seconds=86400)
    assert token is not None
    tokens = token.split(".")
    assert len(tokens) == 3
    j1 = json.loads(base64.decodebytes(tokens[0].encode("utf-8")))
    j2 = json.loads(base64.decodebytes(tokens[1].encode("utf-8")))
    assert j1["alg"] == bumper_isc.TOKEN_JWT_ALG
    assert j1["typ"] == "JWT"
    assert j2["test"] == "data"
    assert j2["t"] == "a"
    assert exp is not None


# --- Tests for get_jwt_details ---
def test_get_jwt_details_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bumper.web.jwt.jwt.decode",
        lambda _, **__: {
            "iat": 1234567890,
            "exp": 1234567990,
            "c": "client1",
            "u": "user1",
            "r": "resource1",
            "ac": "auth123",
        },
    )

    result = get_jwt_details("Bearer valid.token.here")
    assert result == {
        "issued_at": 1234567890,
        "expires_at": 1234567990,
        "client_id": "client1",
        "user_id": "user1",
        "client_resource": "resource1",
        "auth_code": "auth123",
    }


def test_get_jwt_details_missing_bearer() -> None:
    result = get_jwt_details("invalid.token.here")
    assert result is None


def test_get_jwt_details_empty_bearer() -> None:
    result = get_jwt_details("Bearer ")
    assert result is None


def test_get_jwt_details_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_: Any, **__: Any) -> None:
        raise jwt.InvalidTokenError

    monkeypatch.setattr("bumper.web.jwt.jwt.decode", _raise)
    result = get_jwt_details("Bearer token")
    assert result is None


def test_get_jwt_details_none_input() -> None:
    result = get_jwt_details(None)
    assert result is None


# --- Tests for _generate_uid ---
def test_generate_uid_with_account() -> None:
    result = _generate_uid("test_account")
    assert len(result) == 20  # SHA256 hex digest truncated to 20 chars


def test_generate_uid_with_none() -> None:
    result = _generate_uid(None)
    # Should use default username from config
    assert len(result) == 20


# --- Tests for _get_login_details ---
def test_get_login_details_basic() -> None:
    user = models.BumperUser(userid="testuser")
    user.username = "test_username"
    result = _get_login_details("ios", "US", user, "test_token")

    assert result["accessToken"] == "test_token"
    assert result["uid"] == "testuser"
    assert result["username"] == "test_username"
    assert result["country"] == "US"
    assert result["loginName"] == "test_username"


def test_get_login_details_global_app() -> None:
    user = models.BumperUser(userid="testuser")
    user.account_uid = "20240101000000_" + "a" * 32
    user.uc_uid = "20240101000000_" + "b" * 32
    result = _get_login_details("global_ios", "US", user, "test_token")

    assert result["uid"] == user.account_uid
    assert result["ucUid"] == user.uc_uid
    assert result["loginName"] == bumper_isc.USER_USERNAME_DEFAULT
    assert result["mobile"] is None


# --- Tests for _check_token ---
def test_check_token_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.token_repo.verify", lambda _, __: True)

    user = models.BumperUser(userid="testuser")
    user.username = "test_username"
    success, data = _check_token("ios", "US", user, "valid_token")
    assert success is True
    # The check returns the payload; the binder shapes it at the route.
    assert data["loginName"] == "test_username"
    assert data["email"] == bumper_isc.USER_MAIL_DEFAULT


async def test_check_token_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"

    monkeypatch.setattr("bumper.web.auth_service.token_repo.verify", lambda _, __: False)

    success, error = _check_token("ios", "US", DummyUser(), "invalid_token")
    assert success is False
    assert isinstance(error, ApiError)
    assert error.msg == "Parameter error. Please try again later."


# --- Tests for login ---
@pytest.mark.usefixtures("clean_database")
async def test_login_success(webserver_client: TestClient) -> None:
    """A login creates the account with the names the API assigns."""
    async with webserver_client.post(
        "/v1/private/us/en/dev_1234/ios/1/0/0/user/login",
        json={"account": "login_user", "encryptPwd": "x"},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["code"] == "0000"
    assert data["data"]["accessToken"]
    assert is_account_uid(data["data"]["uid"])
    assert is_account_uid(data["data"]["ucUid"])
    assert data["data"]["uid"] != data["data"]["ucUid"]
    assert data["data"]["loginName"] == "login_user"
    user = user_repo.get_by_login_name("login_user")
    assert user is not None
    assert user.account_id == data["data"]["uid"]
    assert "dev_1234" in user.devices


@pytest.mark.usefixtures("clean_database")
async def test_login_binds_the_app_device(webserver_client: TestClient) -> None:
    """Logging in again with the same account keeps one user and one device."""
    async with webserver_client.post(
        "/v1/private/us/en/dev_bind/ios/1/0/0/user/login",
        json={"account": "bind_user", "encryptPwd": "x"},
    ) as resp:
        first = await resp.json()

    async with webserver_client.post(
        "/v1/private/us/en/dev_bind/ios/1/0/0/user/login",
        json={"account": "bind_user", "encryptPwd": "x"},
    ) as resp:
        second = await resp.json()

    assert first["data"]["uid"] == second["data"]["uid"]
    assert len(user_repo.list_all()) == 1
    user = user_repo.get_by_id(first["data"]["uid"])
    assert user is not None
    assert user.devices == ["dev_bind"]


@pytest.mark.usefixtures("clean_database")
async def test_login_adopts_a_presented_public_id_before_generating_one(webserver_client: TestClient) -> None:
    """A legacy account can keep the public id the client already presents."""
    legacy_id = _generate_uid("legacy_login")
    user_repo.add(legacy_id)
    presented_account_id = "20240101000000_" + "a" * 32

    async with webserver_client.get(
        "/v1/private/us/en/dev_legacy/ios/1/0/0/user/login",
        params={"account": "legacy_login", "uid": presented_account_id},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    user = user_repo.get_by_id(legacy_id)
    assert user is not None
    assert user.account_uid == presented_account_id
    assert data["data"]["uid"] == presented_account_id


@pytest.mark.usefixtures("clean_database")
async def test_login_without_account_uses_the_default_account(webserver_client: TestClient) -> None:
    """A client that sends no login name does not create a second account."""
    async with webserver_client.get("/v1/private/us/en/dev_default/ios/1/0/0/user/login") as resp:
        first = await resp.json()

    async with webserver_client.get("/v1/private/us/en/dev_default/ios/1/0/0/user/login") as resp:
        second = await resp.json()

    assert first["code"] == "0000"
    assert first["data"]["uid"] == second["data"]["uid"]
    assert len(user_repo.list_all()) == 1
    user = user_repo.get_by_id(first["data"]["uid"])
    assert user is not None
    assert user.login_name == bumper_isc.USER_USERNAME_DEFAULT


@pytest.mark.usefixtures("clean_database")
async def test_login_reads_the_encrypted_account(webserver_client: TestClient) -> None:
    """The login name the app encrypts is the account the app logs in with."""
    encrypted = _encrypt_account("app-user@example.com")
    async with webserver_client.get(
        "/v2/private/us/en/dev_encrypted/global_e/3.16.0/google_play/1/user/login2",
        params={"encryptAccount": encrypted, "encryptPwd": "x"},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["code"] == "0000"
    assert data["data"]["loginName"] == "app-user@example.com"
    user = user_repo.get_by_login_name("app-user@example.com")
    assert user is not None
    assert user.email == "app-user@example.com"
    assert user.devices == ["dev_encrypted"]


async def _login(webserver_client: TestClient, account: str) -> str:
    """Perform a login and return the userid the server actually assigned."""
    async with webserver_client.post(
        f"/v1/private/us/en/dev_{account}/ecomapp_1234/1/0/0/user/login",
        json={"account": account, "encryptPwd": "x"},
    ) as resp:
        assert resp.status == 200
        body = await resp.json()
        assert body["success"] is True, body
        assert body["data"]["accessToken"]
        return body["data"]["uid"]


async def _login_expired(webserver_client: TestClient, account: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """Log in, then let the token age out, and return the userid.

    Reproduces the steady state the app reaches every `TOKEN_VALIDITY_SECONDS`:
    the user's only token row has been reaped by `revoke_user_expired`, and the
    next auth-code request finds nothing to attach to. A negative validity is
    used so the expiry happens through the production code path rather than by
    hand-editing the table.
    """
    monkeypatch.setattr(bumper_isc, "TOKEN_VALIDITY_SECONDS", -1)
    userid = await _login(webserver_client, account)
    token_repo.revoke_user_expired(userid)
    assert token_repo.get_first(userid) is None
    return userid


@pytest.mark.usefixtures("clean_database")
async def test_auth_code_v2_succeeds_after_token_expired(
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """getAuthCode succeeds after the user's token row was reaped."""
    userid = await _login_expired(webserver_client, "expiry_user", monkeypatch)
    assert userid

    with caplog.at_level(logging.WARNING):
        async with webserver_client.post(
            "/api/users/user.do",
            json={"todo": "GetAuthCode", "auth": {"userid": userid}},
        ) as resp:
            assert resp.status == 200
            data = await resp.json()

    assert data["result"] == "ok"
    assert data["todo"] == "result"
    assert data["code"]
    assert "Failed to create auth_code" not in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_attaches_the_it_token_to_the_presented_client(
    webserver_client: TestClient,
) -> None:
    """The IT token of a client is not written onto another client's row."""
    user = user_repo.create("two_client_user")
    token_repo.add(user.userid, "first_token", client_id="first_client", resource="FIRST")
    token_repo.add(user.userid, "second_token", client_id="second_client", resource="SECOND")

    async with webserver_client.get(
        f"/v1/global/auth/getAuthCode?uid={user.account_id}&accessToken=second_token",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    it_token = data["data"]["authCode"]
    stored = token_repo.get_by_it_token(it_token)
    assert stored is not None
    assert stored.token == "second_token"  # noqa: S105
    assert token_repo.get_by_token("first_token").it_token is None


@pytest.mark.usefixtures("clean_database")
async def test_it_token_names_the_unified_id(
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The IT token answer carries the unified id, not the account id."""
    userid = await _login(webserver_client, "it_user")
    portal = token_repo.get_first(userid)
    assert portal is not None

    with caplog.at_level(logging.WARNING):
        async with webserver_client.get(
            f"/v1/global/auth/getAuthCode?uid={userid}&accessToken={portal.token}",
        ) as resp:
            assert resp.status == 200
            data = await resp.json()

    user = user_repo.get_by_id(userid)
    assert user is not None
    assert data["code"] == "0000"
    assert data["data"]["authCode"].startswith("GLOBAL_APP_ECOVACS_IOT_")
    assert data["data"]["ecovacsUid"] == user.uc_uid
    assert "Failed to create it_token" not in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code_rejects_a_reaped_token(
    webserver_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reaped token cannot buy an IT token; the client has to log in again."""
    userid = await _login_expired(webserver_client, "reaped_user", monkeypatch)
    portal = token_repo.get_first(userid)
    assert portal is None

    async with webserver_client.get(
        f"/v1/global/auth/getAuthCode?uid={userid}&accessToken=expired",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["code"] == "0004"
    assert data["msg"] == "Expired user login"


@pytest.mark.usefixtures("clean_database")
async def test_auth_code_v2_reuses_existing_code(webserver_client: TestClient) -> None:
    """A live token's auth code is reused rather than rotated on every call."""
    userid = await _login(webserver_client, "reuse_user")
    payload = {"todo": "GetAuthCode", "auth": {"userid": userid}}

    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        first = (await resp.json())["code"]

    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        second = (await resp.json())["code"]

    assert first == second
    assert first


@pytest.mark.usefixtures("clean_database")
async def test_auth_code_v2_re_provisions_after_reap(
    webserver_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After a re-provisioned code, oauth_callback can still resolve it."""
    userid = await _login_expired(webserver_client, "cycle_user", monkeypatch)

    async with webserver_client.post(
        "/api/users/user.do",
        json={"todo": "GetAuthCode", "auth": {"userid": userid}},
    ) as resp:
        auth_code = (await resp.json())["code"]

    # oauth_callback resolves an auth code through token_repo; a token row must
    # exist for it to be found.
    assert token_repo.get_by_auth_code(auth_code) is not None


@pytest.mark.usefixtures("clean_database")
async def test_unknown_user_still_rejected(webserver_client: TestClient) -> None:
    """An unknown user id is rejected."""
    async with webserver_client.post(
        "/api/users/user.do",
        json={"todo": "GetAuthCode", "auth": {"userid": "nosuchuser"}},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["result"] == "fail"
        assert data["errno"] == "1004"


@pytest.mark.usefixtures("clean_database")
async def test_oauth_callback_after_expiry(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Full cycle: login, expiry, re-provisioned auth code, oauth callback."""
    userid = await _login_expired(webserver_client, "full_cycle", monkeypatch)

    async with webserver_client.post(
        "/api/users/user.do",
        json={"todo": "GetAuthCode", "auth": {"userid": userid}},
    ) as resp:
        auth_code = (await resp.json())["code"]

    async with webserver_client.get(f"/api/appsvr/oauth_callback?code={auth_code}") as resp:
        assert resp.status == 200
        data = await resp.json()

    user = user_repo.get_by_id(userid)
    assert user is not None
    assert data["data"]["userId"] == user.iot_id
    assert data["data"]["access_token"]
    assert data["data"]["refresh_token"]


async def test_no_token_churn_under_repeated_calls(webserver_client: TestClient) -> None:
    """Repeated getAuthCode calls must not pile up token rows."""
    userid = await _login(webserver_client, "churn_user")
    payload = {"todo": "GetAuthCode", "auth": {"userid": userid}}
    for _ in range(5):
        async with webserver_client.post("/api/users/user.do", json=payload) as resp:
            assert (await resp.json())["result"] == "ok"
    await asyncio.sleep(0)
    assert len(token_repo.list_for_user(userid)) == 1


async def test_user_repo_still_sees_the_user() -> None:
    """Sanity: the re-provisioning path does not create a second user."""
    uid = _generate_uid("dedupe_user")
    user_repo.add(uid)
    user_repo.add(uid)
    users = [u for u in user_repo.list_all() if u.userid == uid]
    assert len(users) == 1


LEGACY_ACCOUNT_ID = "20181108175916_14f5ff6b7742684c1c93bd731cf7fa16"
LEGACY_IOT_ID = "ckiqxr4cfb062946"


def _has_own_user_record(user_id: str) -> bool:
    """Return whether a user record still carries the id itself."""
    return any(user.userid == user_id for user in user_repo.list_all())


@pytest.mark.usefixtures("clean_database")
async def test_check_login_resolves_device_account(webserver_client: TestClient) -> None:
    """checkLogin with an older name returns the account of the app device."""
    canonical = _generate_uid("bumper")
    user_repo.add(canonical)
    user_repo.bind_device(canonical, "device-check")
    token = _generate_token(canonical)

    async with webserver_client.get(
        f"/v1/private/us/en/device-check/ios/1/0/0/user/checkLogin?uid={LEGACY_ACCOUNT_ID}&accessToken={token}",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    user = user_repo.get_by_id(canonical)
    assert user is not None
    assert data["data"]["uid"] == user.account_id
    assert data["data"]["ucUid"] == user.uc_uid
    assert not _has_own_user_record(LEGACY_ACCOUNT_ID)
    assert user_repo.get_by_id(LEGACY_ACCOUNT_ID).userid == canonical
    assert len(user_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database")
async def test_check_login_merges_duplicate_account(webserver_client: TestClient) -> None:
    """A second record created for the same device is merged away."""
    canonical = _generate_uid("bumper")
    user_repo.add(canonical)
    user_repo.bind_device(canonical, "device-merge")

    user_repo.add(LEGACY_ACCOUNT_ID)
    user_repo.add_device(LEGACY_ACCOUNT_ID, "device-merge")
    user_repo.add_bot(LEGACY_ACCOUNT_ID, "bot-legacy")
    token = _generate_token(canonical)

    async with webserver_client.get(
        f"/v1/private/us/en/device-merge/ios/1/0/0/user/checkLogin?uid={LEGACY_ACCOUNT_ID}&accessToken={token}",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    user = user_repo.get_by_id(canonical)
    assert user is not None
    assert data["data"]["uid"] == user.account_id
    assert not _has_own_user_record(LEGACY_ACCOUNT_ID)
    assert "bot-legacy" in user.bots
    assert len(user_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database")
async def test_check_login_unknown_account_is_rejected(webserver_client: TestClient) -> None:
    """An unknown name on an unknown device does not create an account."""
    async with webserver_client.get(
        f"/v1/private/us/en/device-unknown/ios/1/0/0/user/checkLogin?uid={LEGACY_ACCOUNT_ID}",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["code"] == "0004"
    assert user_repo.list_all() == []


@pytest.mark.usefixtures("clean_database")
async def test_check_login_rejects_an_invalid_supplied_token(webserver_client: TestClient) -> None:
    """A bad session token does not silently create a replacement token."""
    userid = await _login(webserver_client, "invalid_check_token")
    token_count = len(token_repo.list_for_user(userid))

    async with webserver_client.get(
        f"/v1/private/us/en/dev_invalid_check_token/ios/1/0/0/user/checkLogin?uid={userid}&accessToken=invalid",
    ) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["code"] == "0004"
    assert len(token_repo.list_for_user(userid)) == token_count


@pytest.mark.usefixtures("clean_database")
async def test_legacy_auth_code_uses_the_token_account(webserver_client: TestClient) -> None:
    """The token names the account, even when the body carries an older name."""
    userid = await _login(webserver_client, "jwt_account")

    async with webserver_client.post(
        "/api/users/user.do",
        json={"todo": "GetAuthCode", "auth": {"userid": userid}},
    ) as resp:
        auth_code = (await resp.json())["code"]

    async with webserver_client.get(f"/api/appsvr/oauth_callback?code={auth_code}") as resp:
        access_token = (await resp.json())["data"]["access_token"]

    async with webserver_client.post(
        "/api/users/user.do",
        json={"todo": "GetAuthCode", "auth": {"userid": LEGACY_IOT_ID, "token": access_token}},
    ) as resp:
        data = await resp.json()

    assert data["result"] == "ok"
    assert not _has_own_user_record(LEGACY_IOT_ID)
    assert user_repo.get_by_id(LEGACY_IOT_ID).userid == userid


@pytest.mark.usefixtures("clean_database")
async def test_login_by_it_token_returns_the_account(webserver_client: TestClient) -> None:
    """An older name in the body does not become a second account."""
    userid = await _login(webserver_client, "it_account")
    portal = token_repo.get_first(userid)
    assert portal is not None

    async with webserver_client.get(
        f"/v1/global/auth/getAuthCode?uid={userid}&accessToken={portal.token}",
    ) as resp:
        it_token = (await resp.json())["data"]["authCode"]

    async with webserver_client.post(
        "/api/users/user.do",
        json={
            "todo": "loginByItToken",
            "userId": LEGACY_IOT_ID,
            "token": it_token,
            "resource": "resource",
        },
    ) as resp:
        data = await resp.json()

    user = user_repo.get_by_id(userid)
    assert user is not None
    assert data["result"] == "ok"
    assert data["userId"] == user.iot_id
    assert data["token"] == portal.token
    assert data["last"] > 0
    assert not _has_own_user_record(LEGACY_IOT_ID)
    assert user_repo.get_by_id(LEGACY_IOT_ID).userid == userid
