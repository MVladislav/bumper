from types import CoroutineType
from typing import Any

from aiohttp.test_utils import TestClient
import pytest


async def test_get_new_auth_valid(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "testuser"

    monkeypatch.setattr("bumper.web.auth_util.token_repo.login_by_it_token", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_util._generate_auth_code", lambda _: "test_auth_code")

    payload = {"itToken": "valid_it_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"
        assert data.get("authCode") == "test_auth_code"


async def test_get_new_auth_missing_token(webserver_client: TestClient) -> None:
    payload = {"todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "New auth failed, 'itToken' not provided"


async def test_get_new_auth_invalid_token(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_util.token_repo.login_by_it_token", lambda _: None)
    payload = {"itToken": "invalid_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "New auth failed, no token found for it-token"


async def test_get_new_auth_generate_code_fails(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "dummy_user"

    monkeypatch.setattr("bumper.web.auth_util.token_repo.login_by_it_token", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_util._generate_auth_code", lambda _: None)

    payload = {"itToken": "some_token", "todo": "OLoginByITToken"}
    async with webserver_client.post("/newauth.do", json=payload) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "fail"
        assert data.get("error") == "Expired client login"


async def test_get_auth_code_valid(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_util.user_repo.get_by_id", lambda user_id: type("User", (), {"userid": user_id})())
    monkeypatch.setattr("bumper.web.auth_util._generate_it_token", lambda _: "generated_it_token")

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=testuser") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["authCode"] == "generated_it_token"
        assert data["data"]["ecovacsUid"] == "testuser"


async def test_get_auth_code_user_not_found(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_util.user_repo.get_by_id", lambda _: None)
    monkeypatch.setattr("bumper.web.auth_util._fallback_user_by_device_id", lambda _: None)

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=missing") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert data.get("msg").startswith("No user found")


async def test_get_auth_code_token_fail(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_util.user_repo.get_by_id", lambda user_id: type("User", (), {"userid": user_id})())
    monkeypatch.setattr("bumper.web.auth_util._generate_it_token", lambda _: None)

    async with webserver_client.get("/v1/global/auth/getAuthCode?uid=testuser") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("code") == "0004"
        assert not data.get("success")
        assert data.get("msg") == "Expired user login"


async def test_get_auth_code_fallback_user(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bumper.web.auth_util.user_repo.get_by_id", lambda _: None)
    monkeypatch.setattr(
        "bumper.web.auth_util._fallback_user_by_device_id",
        lambda _: type("User", (), {"userid": "from_device"})(),
    )
    monkeypatch.setattr("bumper.web.auth_util._generate_it_token", lambda _: "token_device")

    async with webserver_client.get("/v1/global/auth/getAuthCode?deviceId=device123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["authCode"] == "token_device"
        assert data["data"]["ecovacsUid"] == "from_device"


async def test_oauth_callback_success(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyToken:
        userid = "user1"
        auth_code = "auth123"

    class DummyClient:
        userid = "client_id"
        resource = "client_resource"

    async def dummy_generate_jwt(data: Any, t: str, **args: dict[str, Any]) -> CoroutineType[Any, Any, tuple[str, int]]:  # noqa: ARG001
        return f"{t}_token", 99999999

    monkeypatch.setattr("bumper.web.auth_util.token_repo.get_by_auth_code", lambda _: DummyToken())
    monkeypatch.setattr("bumper.web.auth_util.client_repo.get", lambda _: DummyClient())
    monkeypatch.setattr("bumper.web.auth_util.generate_jwt_helper", dummy_generate_jwt)

    async with webserver_client.get("/api/appsvr/oauth_callback?code=auth123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["data"]["access_token"] == "a_token"  # noqa: S105
        assert data["data"]["refresh_token"] == "r_token"  # noqa: S105
        assert data["data"]["userId"] == "user1"
        assert data["data"]["expire_at"] == 99999999
