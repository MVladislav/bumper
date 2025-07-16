import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid
from bumper.web.response_utils import ERR_TOKEN_INVALID, RETURN_API_SUCCESS

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_check_login(webserver_client: TestClient) -> None:
    # Test without token
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={None}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert jsonresp["data"]["accessToken"] != "token_1234"
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # Add a user to db and test with existing users
    user_repo.add(USER_ID)
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={None}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert jsonresp["data"]["accessToken"] != "token_1234"
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin?accessToken={None}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert jsonresp["data"]["accessToken"] != "token_1234"
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # Remove dev from example user
    user_repo.remove_device(USER_ID, "dev_1234")

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={'token_1234'}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert jsonresp["data"]["accessToken"] == "token_1234"
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin?accessToken={'token_1234'}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert jsonresp["data"]["accessToken"] == "token_1234"
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code(webserver_client: TestClient) -> None:
    # Test without user or token
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid={None}&accessToken={None}")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == ERR_TOKEN_INVALID

    # # Test as global_e
    # resp = await webserver_client.get(f"/v1/global/auth/getAuthCode?uid={None}&deviceId=dev_1234")
    # assert resp.status == 200
    # text = await resp.text()
    # jsonresp = json.loads(text)
    # assert jsonresp["code"] == ERR_TOKEN_INVALID

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "authCode" in jsonresp["data"]
    assert "ecovacsUid" in jsonresp["data"]

    # The above should have added an authcode to token, try again to test with existing authcode
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "authCode" in jsonresp["data"]
    assert "ecovacsUid" in jsonresp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_check_agreement(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/checkAgreement")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS

    # Test as global_e
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkAgreement")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_user_account_info(webserver_client: TestClient) -> None:
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    token_repo.add_auth_code(USER_ID, "auth_1234")
    user_repo.add_bot(USER_ID, "did_1234")
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")

    resp = await webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/getUserAccountInfo")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == "0000"
    assert jsonresp["msg"] == "The operation was successful"
    assert jsonresp["data"]["uid"] == USER_ID
