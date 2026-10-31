"""Tests for bumper/web/plugins/api/rapp.py."""

from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json


@pytest.mark.usefixtures("clean_database")
async def test_user_data_map_get_returns_the_home(webserver_client: TestClient) -> None:
    """The map endpoint answers with the placeholder home."""
    status, body = await get_json(webserver_client, "/api/rapp/sds/user/data/map/get")
    assert status == 200
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["data"] == {"data": {"name": "My Home"}, "tag": None}


@pytest.mark.usefixtures("clean_database")
async def test_user_data_del_acknowledges_without_payload(webserver_client: TestClient) -> None:
    """The delete endpoint answers with an empty payload."""
    status, body = await get_json(webserver_client, "/api/rapp/sds/user/data/del")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] is None


@pytest.mark.usefixtures("clean_database")
async def test_user_data_list_returns_one_stored_entry(webserver_client: TestClient) -> None:
    """The list endpoint answers with one entry and millisecond timestamps."""
    status, body = await get_json(webserver_client, "/api/rapp/sds/user/data/list")
    assert status == 200
    assert body["code"] == 0
    entries = body["data"]
    assert len(entries) == 1
    assert entries[0]["key"] == "iwashere"
    assert entries[0]["data"] is None
    assert isinstance(entries[0]["createTime"], int)
    assert isinstance(entries[0]["updateTime"], int)
