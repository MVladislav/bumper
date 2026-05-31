import base64
import json
from types import CoroutineType
from typing import Any

from aiohttp.test_utils import TestClient
import pytest

from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import (
    _check_token,
    _generate_auth_code,
    _generate_uid,
    _get_login_details,
    generate_jwt_helper,
    get_jwt_details,
)
from bumper.web.utils import models


# --- Tests for newauth.do ---
async def test_get_new_auth_valid(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "testuser"
        auth_code = None

    monkeypatch.setattr("bumper.web.auth_service.token_repo.login_by_it_token", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda _: "test_auth_code")

    payload = {"itToken": "valid_it_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"
        assert data.get("authCode") == "test_auth_code"


async def test_get_existing_auth_valid(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "testuser"
        auth_code = "existingToken"

    monkeypatch.setattr("bumper.web.auth_service.token_repo.login_by_it_token", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda _: "existingToken")

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


async def test_get_new_auth_generate_code_fails(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "dummy_user"
        auth_code = None

    monkeypatch.setattr("bumper.web.auth_service.token_repo.login_by_it_token", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda _: None)

    payload = {"itToken": "some_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "Expired client login"


# --- Tests for getAuthCode ---
async def test_get_auth_code_valid(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda user_id: type("User", (), {"userid": user_id})())
    monkeypatch.setattr("bumper.web.auth_service._generate_it_token", lambda _: "generated_it_token")

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=testuser") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["authCode"] == "generated_it_token"
        assert data["data"]["ecovacsUid"] == "testuser"


async def test_get_auth_code_user_not_found(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service._fallback_user_by_device_id", lambda _: None)

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=missing") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert data.get("msg").startswith("No user found")


async def test_get_auth_code_token_fail(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda user_id: type("User", (), {"userid": user_id})())
    monkeypatch.setattr("bumper.web.auth_service._generate_it_token", lambda _: None)

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=testuser") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert not data.get("success")
        assert data.get("msg") == "Expired user login"


async def test_get_auth_code_fallback_user(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: None)
    monkeypatch.setattr(
        "bumper.web.auth_service._fallback_user_by_device_id",
        lambda _: type("User", (), {"userid": "from_device"})(),
    )
    monkeypatch.setattr("bumper.web.auth_service._generate_it_token", lambda _: "token_device")

    async with webserver_client.get("/v1/global/auth/getAuthCode?deviceId=device123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["authCode"] == "token_device"
        assert data["data"]["ecovacsUid"] == "from_device"


# --- Tests for get_auth_code_v2 ---
async def test_get_auth_code_v2_valid_user(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"
        username = "test_username"

    class DummyToken:
        auth_code = "existing_auth_code"

    # Mock the dependencies
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: DummyUser())
    monkeypatch.setattr("bumper.web.auth_service.token_repo.revoke_user_expired", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service.token_repo.get_first", lambda _: DummyToken())

    # Call via the actual endpoint
    payload = {"todo": "GetAuthCode", "auth": {"userid": "testuser"}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"
        assert data.get("code") == "existing_auth_code"


async def test_get_auth_code_v2_valid_user_no_token(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"
        username = "test_username"

    # Mock the dependencies
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: DummyUser())
    monkeypatch.setattr("bumper.web.auth_service.token_repo.revoke_user_expired", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service.token_repo.get_first", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda _: "new_auth_code")

    # Call via the actual endpoint
    payload = {"todo": "GetAuthCode", "auth": {"userid": "testuser"}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"
        assert data.get("code") == "new_auth_code"  # Note: This endpoint returns "code" not "authCode"


async def test_get_auth_code_v2_user_not_found(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock the dependencies
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: None)

    # Call via the actual endpoint
    payload = {"todo": "GetAuthCode", "auth": {"userid": "nonexistent"}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("errno") == "1004"  # ERR_USER_DISABLE
        assert "No user found" in data.get("error")


async def test_get_auth_code_v2_auth_error(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"
        username = "test_username"

    # Mock the dependencies
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: DummyUser())
    monkeypatch.setattr("bumper.web.auth_service.token_repo.revoke_user_expired", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service.token_repo.get_first", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service._generate_auth_code", lambda _: None)

    # Call via the actual endpoint
    payload = {"todo": "GetAuthCode", "auth": {"userid": "testuser"}}
    async with webserver_client.post("/api/users/user.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("errno") == "1004"  # ERR_USER_DISABLE
        assert data.get("error") == "Auth error"


# --- Tests for oauth_callback ---
async def test_oauth_callback_success(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "user1"
        auth_code = "auth123"

    class DummyClient:
        userid = "client_id"
        resource = "client_resource"

    async def dummy_generate_jwt(data: Any, t: str, **args: dict[str, Any]) -> CoroutineType[Any, Any, tuple[str, int]]:  # noqa: ARG001
        return f"{t}_token", 99999999

    monkeypatch.setattr("bumper.web.auth_service.token_repo.get_by_auth_code", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_service.client_repo.get", lambda _: DummyClient())
    monkeypatch.setattr("bumper.web.auth_service.generate_jwt_helper", dummy_generate_jwt)

    async with webserver_client.get("/api/appsvr/oauth_callback?code=auth123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["access_token"] == "a_token"  # noqa: S105
        assert data["data"]["refresh_token"] == "r_token"  # noqa: S105
        assert data["data"]["userId"] == "user1"
        assert data["data"]["expire_at"] == 99999999


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


# --- Tests for get_jwt_details and _extract_jwt_details---
def test_get_jwt_details_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bumper.web.auth_service.jwt.decode",
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
    result = _get_login_details("ios", "US", user, "test_token")

    assert result["accessToken"] == "test_token"
    assert result["uid"] == "testuser"
    assert result["username"] == bumper_isc.USER_USERNAME_DEFAULT
    assert result["country"] == "US"
    assert result["loginName"] == "testuser"


def test_get_login_details_global_app() -> None:
    user = models.BumperUser(userid="testuser")
    result = _get_login_details("global_ios", "US", user, "test_token")

    assert result["ucUid"] == "testuser"
    assert result["loginName"] == bumper_isc.USER_USERNAME_DEFAULT
    assert result["mobile"] is None


# --- Tests for _check_token ---
def test_check_token_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.token_repo.verify", lambda _, __: True)

    user = models.BumperUser(userid="testuser")
    success, response = _check_token("ios", "US", user, "valid_token")
    assert success is True
    assert response.status == 200
    data = json.loads(response.text)
    assert data["data"]["loginName"] == "testuser"
    assert data["data"]["email"] == bumper_isc.USER_MAIL_DEFAULT


async def test_check_token_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"

    monkeypatch.setattr("bumper.web.auth_service.token_repo.verify", lambda _, __: False)

    success, response = _check_token("ios", "US", DummyUser(), "invalid_token")
    assert success is False
    assert response.status == 200
    data = json.loads(response.text)
    assert data["msg"] == "Parameter error. Please try again later."


# --- Tests for login ---
async def test_login_success(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"
        username = "test_username"

    monkeypatch.setattr("bumper.web.auth_service.bumper_isc.USE_AUTH", False)
    monkeypatch.setattr("bumper.web.auth_service._generate_uid", lambda _: "testuser")
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_id", lambda _: DummyUser())
    monkeypatch.setattr("bumper.web.auth_service.user_repo.add", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_service._auth_any_user_extends", lambda _, __: None)
    monkeypatch.setattr("bumper.web.auth_service._generate_token", lambda _: "test_token")
    monkeypatch.setattr(
        "bumper.web.auth_service._get_login_details",
        lambda *_: {"accessToken": "test_token", "uid": "testuser"},
    )

    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == "0000"
        assert data["data"]["accessToken"] == "test_token"


async def test_login_with_auth(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        userid = "testuser"
        username = "test_username"

    monkeypatch.setattr("bumper.web.auth_service.bumper_isc.USE_AUTH", True)
    monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_device_id", lambda _: DummyUser())
    monkeypatch.setattr("bumper.web.auth_service.token_repo.revoke_user_expired", lambda _: None)
    monkeypatch.setattr(
        "bumper.web.auth_service._get_login_details",
        lambda *_: {"accessToken": "auth_token", "uid": "testuser"},
    )
    monkeypatch.setattr("bumper.web.auth_service._generate_token", lambda _: "auth_token")

    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == "0000"
        assert data["data"]["accessToken"] == "auth_token"


async def test_login_no_user(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_service.bumper_isc.USE_AUTH", True)
    # monkeypatch.setattr("bumper.web.auth_service.user_repo.get_by_device_id", lambda _: None)

    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == "0004"  # ERR_TOKEN_INVALID
