from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_get_users_api(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/users/user.do", json={}) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "fail"


@pytest.mark.usefixtures("clean_database")
async def test_post_users_api(webserver_client: TestClient) -> None:
    # Test FindBest
    postbody = {"todo": "FindBest", "service": "EcoMsgNew"}
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test EcoUpdate
    postbody = {"todo": "FindBest", "service": "EcoUpdate"}
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test loginByItToken - Uses the authcode
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    token_repo.add_it_token(USER_ID, "auth_1234")
    user_repo.add_bot(USER_ID, "did_1234")
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")
    # Test
    postbody = {
        "country": "US",
        "last": "",
        "realm": "ecouser.net",
        "resource": "dev_1234",
        "todo": "loginByItToken",
        "token": "auth_1234",
        "userId": USER_ID,
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test as EcoVacs Home (global_e)
    postbody = {
        "country": "US",
        "edition": "ECOGLOBLE",
        "last": "",
        "org": "ECOWW",
        "resource": "dev_1234",
        "todo": "loginByItToken",
        "token": "auth_1234",
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test as EcoVacs Home (global_e) & Post Form
    postbody = {
        "country": "US",
        "edition": "ECOGLOBLE",
        "last": "",
        "org": "ECOWW",
        "resource": "dev_1234",
        "todo": "loginByItToken",
        "token": "auth_1234",
    }
    async with webserver_client.post("/api/users/user.do", data=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test GetDeviceList
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "dev_1234",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "todo": "GetDeviceList",
        "userid": USER_ID,
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test SetDeviceNick
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "dev_1234",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "todo": "SetDeviceNick",
        "nick": "botnick",
        "did": "did_1234",
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test AddOneDevice - Same as set nick for some bots
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "dev_1234",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "todo": "AddOneDevice",
        "nick": "botnick",
        "did": "did_1234",
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"

    # Test DeleteOneDevice - remove bot
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "dev_1234",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "todo": "DeleteOneDevice",
        "did": "did_1234",
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["result"] == "ok"
