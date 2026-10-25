from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid

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

    user_repo.add("second_user")

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
    second_user = user_repo.get_by_id("second_user")
    assert second_user is not None
    assert "did_1234" in second_user.bots


@pytest.mark.usefixtures("clean_database")
async def test_get_users_info_returns_the_members(webserver_client: TestClient) -> None:
    """The app asks for the members it knows the ids of."""
    user_repo.add("uid_one")
    user_repo.add("uid_two")

    postbody = {"todo": "GetUsersInfo", "users": ["uid_one"], "auth": {"with": "password", "userid": "IOTSDK"}}
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["result"] == "ok"
    assert json_resp["todo"] == "result"
    users = json_resp["users"]
    assert len(users) == 1
    assert users[0]["uid"] == "uid_one"
    assert users[0]["nick"] == bumper_isc.USER_NICKNAME_DEFAULT
    assert users[0]["isAdmin"] is True


@pytest.mark.usefixtures("clean_database")
async def test_get_users_info_without_a_filter_returns_every_member(webserver_client: TestClient) -> None:
    """Without the id list every member is returned."""
    user_repo.add("uid_one")
    user_repo.add("uid_two")

    postbody = {"todo": "GetUsersInfo", "auth": {"with": "password", "userid": "IOTSDK"}}
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        json_resp = await resp.json()

    assert {user["uid"] for user in json_resp["users"]} == {"uid_one", "uid_two"}


@pytest.mark.usefixtures("clean_database")
async def test_get_users_info_carries_the_stored_nickname(webserver_client: TestClient) -> None:
    """The nickname is the display name the app shows."""
    user_repo.add("uid_one")
    user_repo.set_nickname("uid_one", "Kitchen robot")

    postbody = {"todo": "GetUsersInfo", "users": ["uid_one"], "auth": {"with": "password", "userid": "IOTSDK"}}
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        json_resp = await resp.json()

    assert json_resp["users"][0]["nick"] == "Kitchen robot"


@pytest.mark.usefixtures("clean_database")
async def test_modify_user_nickname(webserver_client: TestClient) -> None:
    """The app renames the user from the profile screen."""
    user_repo.add("uid_one")

    async with webserver_client.get(
        "/v1/private/DE/EN/dev_1234/global_e/3.15.1/google_play/1/user/center/modifyUserNickname",
        params={"uid": "uid_one", "nickname": "Kitchen robot"},
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["code"] == "0000"
    assert user_repo.get_by_id("uid_one").nickname == "Kitchen robot"


@pytest.mark.usefixtures("clean_database")
async def test_logout_revokes_only_the_named_client(webserver_client: TestClient) -> None:
    """One client can log out without logging out the other clients."""
    user = user_repo.create("logout_user")
    token_repo.add(user.userid, "token_one", client_id="client_one", resource="RES_ONE")
    token_repo.add(user.userid, "token_two", client_id="client_two", resource="RES_TWO")
    client_repo.add("client_one", user.userid, "ecouser.net", "RES_ONE", client_id="client_one")
    client_repo.add("client_two", user.userid, "ecouser.net", "RES_TWO", client_id="client_two")

    postbody = {
        "todo": "logout",
        "auth": {"userid": user.account_id, "token": "token_one"},
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200
        data = await resp.json()

    assert data["result"] == "ok"
    assert token_repo.get_by_token("token_one") is None
    assert token_repo.get_by_token("token_two") is not None
    assert client_repo.get(user.userid, client_id="client_one") is None
    assert client_repo.get(user.userid, client_id="client_two") is not None
    assert user_repo.get_by_id(user.userid) is not None


@pytest.mark.usefixtures("clean_database")
async def test_logout_with_an_unknown_token_keeps_every_client(webserver_client: TestClient) -> None:
    """A stale token cannot log out the whole account."""
    user = user_repo.create("stale_logout_user")
    token_repo.add(user.userid, "token_one", client_id="client_one", resource="RES_ONE")
    client_repo.add("client_one", user.userid, "ecouser.net", "RES_ONE", client_id="client_one")

    postbody = {
        "todo": "logout",
        "auth": {"userid": user.account_id, "token": "unknown"},
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200

    assert token_repo.get_by_token("token_one") is not None
    assert client_repo.get(user.userid, client_id="client_one") is not None


@pytest.mark.usefixtures("clean_database")
async def test_logout_of_a_legacy_token_does_not_remove_all_clients(webserver_client: TestClient) -> None:
    """A token without client metadata cannot identify unrelated client rows."""
    user = user_repo.create("legacy_logout_user")
    token_repo.add(user.userid, "legacy_token")
    client_repo.add("client_one", user.userid, "ecouser.net", "RES_ONE", client_id="client_one")
    client_repo.add("client_two", user.userid, "ecouser.net", "RES_TWO", client_id="client_two")

    postbody = {
        "todo": "logout",
        "auth": {"userid": user.account_id, "token": "legacy_token"},
    }
    async with webserver_client.post("/api/users/user.do", json=postbody) as resp:
        assert resp.status == 200

    assert token_repo.get_by_token("legacy_token") is None
    assert len(client_repo.list_for_user(user.userid)) == 2
