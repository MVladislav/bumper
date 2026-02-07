from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid
from bumper.web.utils.response_helper import ERR_TOKEN_INVALID, RETURN_API_SUCCESS

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_check_login(webserver_client: TestClient) -> None:
    # Test without token
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={None}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] != "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Add a user to db and test with existing users
    user_repo.add(USER_ID)
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={None}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] != "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin?accessToken={None}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] != "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Remove dev from example user
    user_repo.remove_device(USER_ID, "dev_1234")

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={'token_1234'}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] == "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    async with webserver_client.get(
        f"/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin?accessToken={'token_1234'}",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] == "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code(webserver_client: TestClient) -> None:
    # Test without user or token
    async with webserver_client.get(
        f"/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid={None}&accessToken={None}",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == ERR_TOKEN_INVALID

        # # Test as global_e
        # async with webserver_client.get(f"/v1/global/auth/getAuthCode?uid={None}&deviceId=dev_1234") as resp:
        # assert resp.status == 200
        # json_resp = await resp.json()
        # assert json_resp["code"] == ERR_TOKEN_INVALID

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "authCode" in json_resp["data"]
        assert "ecovacsUid" in json_resp["data"]

    # The above should have added an authcode to token, try again to test with existing authcode
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "authCode" in json_resp["data"]
        assert "ecovacsUid" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_check_agreement(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/checkAgreement") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS

    # Test as global_e
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkAgreement") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_user_account_info(webserver_client: TestClient) -> None:
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    token_repo.add_auth_code(USER_ID, "auth_1234")
    user_repo.add_bot(USER_ID, "did_1234")
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")

    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/getUserAccountInfo") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == "0000"
        assert json_resp["msg"] == "The operation was successful"
        assert json_resp["data"]["uid"] == USER_ID
