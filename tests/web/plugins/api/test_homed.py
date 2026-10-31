"""Tests for bumper/web/plugins/api/homed.py"""

from datetime import datetime

from aiohttp.test_utils import TestClient
import jwt
import pytest

from bumper.db import bot_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.payloads import HOME_ROLE_IDS, HOME_ROLE_IDS_NAMED
from tests.web.helpers import get_json


def _bearer_with_auth_code(auth_code: str) -> str:
    """Return the authorization header value of a signed access token."""
    now = int(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())
    token = jwt.encode(
        {"ac": auth_code, "t": "a", "iat": now, "exp": now + 60},
        bumper_isc.server_key.read_text(encoding="utf-8"),
        algorithm=bumper_isc.TOKEN_JWT_ALG,
    )
    return f"Bearer {token}"


@pytest.mark.usefixtures("clean_database")
async def test_home_role_list_returns_the_home_roles(webserver_client: TestClient) -> None:
    """The role list feeds the role id the member list shows."""
    status, body = await get_json(webserver_client, "/api/homed/home/role/list")
    assert status == 200
    assert body["code"] == 0
    assert body["message"] == "success"
    roles = body["data"]
    assert len(roles) == 10
    assert roles[0] == {"id": HOME_ROLE_IDS[0], "name": "Fraternal grandpa", "isUse": False}
    assert [role["name"] for role in roles] == [name for _, name in HOME_ROLE_IDS_NAMED]
    assert all(role["isUse"] is False for role in roles)


@pytest.mark.usefixtures("clean_database")
async def test_member_list_uses_a_role_id(webserver_client: TestClient) -> None:
    """The member list carries a role id of the expected shape, not a placeholder."""
    user_repo.add("uid_role")
    user = user_repo.get_by_id("uid_role")
    user_repo.add_home_id(user.userid, bumper_isc.DEFAULT_HOME_ID)

    status, body = await get_json(webserver_client, f"/api/homed/member/list?homeId={bumper_isc.DEFAULT_HOME_ID}")
    assert status == 200

    member = body["data"][0]
    assert member["roleId"] in HOME_ROLE_IDS
    assert member["roleId"] != "xxx"
    assert member["roleName"] == "Fraternal grandpa"


@pytest.mark.usefixtures("clean_database")
async def test_home_member_role_update_acknowledges(webserver_client: TestClient) -> None:
    async with webserver_client.post(
        "/api/homed/home/member/role/update",
        json={"homeId": "h", "uid": "u", "roleId": HOME_ROLE_IDS[0]},
    ) as resp:
        assert resp.status == 200
        body = await resp.json()
        assert body["code"] == 0


@pytest.mark.usefixtures("clean_database")
async def test_member_list_unknown_home_still_errors(webserver_client: TestClient) -> None:
    """An unknown home still fails."""
    bot_repo.add("sn_x", "did_x", "p95mgv", "res1", "eco-ng")
    async with webserver_client.get("/api/homed/member/list?homeId=nope") as resp:
        assert resp.status == 500


@pytest.mark.usefixtures("clean_database")
async def test_member_list_uses_the_stored_nickname(webserver_client: TestClient) -> None:
    """The member name follows the account, not a hard-coded constant."""
    user_repo.add("uid_nick")
    user_repo.add_home_id("uid_nick", bumper_isc.DEFAULT_HOME_ID)
    user_repo.set_nickname("uid_nick", "Kitchen robot")

    status, body = await get_json(webserver_client, f"/api/homed/member/list?homeId={bumper_isc.DEFAULT_HOME_ID}")
    assert status == 200
    assert body["data"][0]["name"] == "Kitchen robot"


@pytest.mark.usefixtures("clean_database")
async def test_matter_paa_returns_an_empty_document(webserver_client: TestClient) -> None:
    """The Matter PAA endpoint answers with an empty document."""
    status, body = await get_json(webserver_client, "/api/homed/v2/matter/paa")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == {}


@pytest.mark.usefixtures("clean_database")
async def test_matter_fabric_reports_no_supported_devices(webserver_client: TestClient) -> None:
    """The current account has no devices supporting local Matter fabric."""
    status, body = await get_json(webserver_client, "/api/homed/v2/matter/fabric")
    assert status == 200
    assert body == {
        "code": 4007,
        "message": "There are no devices that support LAN mode under this username.",
    }


@pytest.mark.usefixtures("clean_database")
async def test_home_list_returns_the_homes_of_the_user(webserver_client: TestClient) -> None:
    """The home list carries the homes stored on the account it is asked for."""
    user_repo.add("uid_list")
    user_repo.add_home_id("uid_list", "home_a")
    user_repo.add_home_id("uid_list", "home_b")
    user = user_repo.get_by_id("uid_list")
    assert user is not None

    status, body = await get_json(webserver_client, "/api/homed/home/list?userid=uid_list")
    assert status == 200
    assert body["code"] == 0
    homes = body["data"]
    assert [home["homeId"] for home in homes] == ["781a0733923f2240cf304757", "home_a", "home_b"]
    assert [home["name"] for home in homes] == ["My Home (0)", "My Home (1)", "My Home (2)"]
    assert all(home["createUser"] == user.iot_id for home in homes)
    assert all(home["type"] == "own" for home in homes)


@pytest.mark.usefixtures("clean_database")
async def test_home_list_without_userid_is_empty(webserver_client: TestClient) -> None:
    """A home list without an account names nobody and comes back empty."""
    status, body = await get_json(webserver_client, "/api/homed/home/list")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_home_list_unknown_user_is_empty(webserver_client: TestClient) -> None:
    """A home list for an unknown account comes back empty, not as a failure."""
    status, body = await get_json(webserver_client, "/api/homed/home/list?userid=uid_missing")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_home_create_without_a_verified_token_is_rejected(webserver_client: TestClient) -> None:
    """A caller that carries no verifiable token may not create a home."""
    async with webserver_client.post("/api/homed/home/create", json={"name": "New home"}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body == {"ret": "fail", "todo": "result", "code": 1, "error": "Auth error"}


@pytest.mark.usefixtures("clean_database")
async def test_home_create_adds_a_home_to_the_user_of_the_token(webserver_client: TestClient) -> None:
    """The new home lands on the account the token carries."""
    user_repo.add("uid_create")
    token_repo.add("uid_create", "portal_token")
    token_repo.add_auth_code("uid_create", "auth_code_1")
    headers = {"Authorization": _bearer_with_auth_code("auth_code_1")}

    async with webserver_client.post("/api/homed/home/create", json={"name": "New home"}, headers=headers) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    user = user_repo.get_by_id("uid_create")
    assert user is not None
    assert len(user.homeids) == 2
    assert len(user.homeids[1]) == 32  # uuid4().hex


@pytest.mark.usefixtures("clean_database")
async def test_home_create_with_an_unknown_auth_code_adds_nothing(webserver_client: TestClient) -> None:
    """A token whose auth code no session carries buys no home."""
    user_repo.add("uid_create_none")
    headers = {"Authorization": _bearer_with_auth_code("no_such_code")}

    async with webserver_client.post("/api/homed/home/create", json={"name": "New home"}, headers=headers) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    user = user_repo.get_by_id("uid_create_none")
    assert user is not None
    assert user.homeids == ["781a0733923f2240cf304757"]


@pytest.mark.usefixtures("clean_database")
async def test_home_update_acknowledges(webserver_client: TestClient) -> None:
    """The update is acknowledged even though it changes nothing yet."""
    async with webserver_client.post("/api/homed/home/update", json={"homeId": "h_upd", "name": "Renamed"}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["message"] == "success"


@pytest.mark.usefixtures("clean_database")
async def test_home_delete_removes_the_home_of_the_user(webserver_client: TestClient) -> None:
    """The delete takes the home off the account that owns it."""
    user_repo.add("uid_del")
    user_repo.add_home_id("uid_del", "h_del")

    async with webserver_client.post("/api/homed/home/delete", json={"homeId": "h_del"}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    user = user_repo.get_by_id("uid_del")
    assert user is not None
    assert user.homeids == ["781a0733923f2240cf304757"]


@pytest.mark.usefixtures("clean_database")
async def test_home_delete_unknown_home_still_succeeds(webserver_client: TestClient) -> None:
    """Deleting a home nobody owns is still acknowledged."""
    async with webserver_client.post("/api/homed/home/delete", json={"homeId": "nope"}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0


@pytest.mark.usefixtures("clean_database")
async def test_device_move_acknowledges(webserver_client: TestClient) -> None:
    """The device move is acknowledged with the device and target it names."""
    async with webserver_client.post(
        "/api/homed/device/move",
        json={"did": "did_move", "mid": "mid_move", "to": "home_target"},
    ) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
