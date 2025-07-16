import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid
from bumper.web.response_utils import RETURN_API_SUCCESS

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_login_with_user(webserver_client: TestClient) -> None:
    # Test without user
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_login_without_user(webserver_client: TestClient) -> None:
    # Test global_e without user
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/login")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_login_with_existing_user(webserver_client: TestClient) -> None:
    # Add a user to db and test with existing users
    user_repo.add(USER_ID)
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # Add a bot to db that will be added to user
    bot_repo.add("sn_123", "did_123", "dev_123", "res_123", "com_123")
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
    assert "accessToken" in jsonresp["data"]
    assert "uid" in jsonresp["data"]
    assert "username" in jsonresp["data"]

    # # Add a bot to db that doesn't have a did
    # newbot = {
    #     "class": "dev_1234",
    #     "company": "com_123",
    #     # "did": self.did,
    #     "name": "sn_1234",
    #     "resource": "res_1234",
    # }
    # db2.bot_full_upsert(VacBotDevice.from_dict(newbot))
    # bot_repo._upsert(newbot, QueryInstance.did == did)

    # resp = await webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/login")
    # assert resp.status == 200
    # text = await resp.text()
    # jsonresp = json.loads(text)
    # assert jsonresp["code"] == RETURN_API_SUCCESS
    # assert "accessToken" in jsonresp["data"]
    # assert "uid" in jsonresp["data"]
    # assert "username" in jsonresp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_logout(webserver_client: TestClient) -> None:
    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    resp = await webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/logout?accessToken={'token_1234'}")

    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
