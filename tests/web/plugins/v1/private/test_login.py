from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid
from bumper.web.envelope import RETURN_API_SUCCESS
from tests.web.helpers import get_json

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_login_with_user(webserver_client: TestClient) -> None:
    status, json_resp = await get_json(webserver_client, "/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in json_resp["data"]
    assert "uid" in json_resp["data"]
    assert "username" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_login_without_user(webserver_client: TestClient) -> None:
    status, json_resp = await get_json(webserver_client, "/v1/private/us/en/dev_1234/global_e/1/0/0/user/login")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in json_resp["data"]
    assert "uid" in json_resp["data"]
    assert "username" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_login_with_existing_user(webserver_client: TestClient) -> None:
    user_repo.add(USER_ID)
    status, json_resp = await get_json(webserver_client, "/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in json_resp["data"]
    assert "uid" in json_resp["data"]
    assert "username" in json_resp["data"]

    bot_repo.add("sn_123", "did_123", "dev_123", "res_123", "com_123")
    status, json_resp = await get_json(webserver_client, "/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in json_resp["data"]
    assert "uid" in json_resp["data"]
    assert "username" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_logout(webserver_client: TestClient) -> None:
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    status, json_resp = await get_json(
        webserver_client,
        f"/v1/private/us/en/dev_1234/ios/1/0/0/user/logout?accessToken={'token_1234'}",
    )
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
