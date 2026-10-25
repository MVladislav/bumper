"""Tests for bumper/web/plugins/api/homed.py"""

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.payloads import HOME_ROLE_IDS, HOME_ROLE_IDS_NAMED


@pytest.mark.usefixtures("clean_database")
async def test_home_role_list_returns_the_home_roles(webserver_client: TestClient) -> None:
    """The role list feeds the role id the member list shows."""
    async with webserver_client.get("/api/homed/home/role/list") as resp:
        assert resp.status == 200
        body = await resp.json()

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

    async with webserver_client.get(f"/api/homed/member/list?homeId={bumper_isc.DEFAULT_HOME_ID}") as resp:
        assert resp.status == 200
        body = await resp.json()

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

    async with webserver_client.get(f"/api/homed/member/list?homeId={bumper_isc.DEFAULT_HOME_ID}") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["data"][0]["name"] == "Kitchen robot"


@pytest.mark.usefixtures("clean_database")
async def test_matter_paa_returns_an_empty_document(webserver_client: TestClient) -> None:
    """The Matter PAA endpoint answers with an empty document."""
    async with webserver_client.get("/api/homed/v2/matter/paa") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["data"] == {}


@pytest.mark.usefixtures("clean_database")
async def test_matter_fabric_reports_no_supported_devices(webserver_client: TestClient) -> None:
    """The current account has no devices supporting local Matter fabric."""
    async with webserver_client.get("/api/homed/v2/matter/fabric") as response:
        assert response.status == 200
        assert await response.json() == {
            "code": 4007,
            "message": "There are no devices that support LAN mode under this username.",
        }
