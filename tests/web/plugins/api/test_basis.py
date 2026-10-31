"""Tests for bumper/web/plugins/api/basis.py"""

from aiohttp.test_utils import TestClient

from tests.web.helpers import get_json


async def test_get_by_area(webserver_client: TestClient) -> None:
    """A known area is answered with its data centre code."""
    status, body = await get_json(webserver_client, "/api/basis/dc/get-by-area?area=de")
    assert status == 200
    assert body["code"] == 0
    assert body["data"]["dc"]


async def test_get_by_area_rejects_an_unknown_area(webserver_client: TestClient) -> None:
    """An unknown area is answered with the list of the known ones."""
    status, body = await get_json(webserver_client, "/api/basis/dc/get-by-area?area=zz")
    assert status == 200
    assert body["code"] == 4000
    assert "area" in body["msg"]


async def test_get_timezones(webserver_client: TestClient) -> None:
    """The timezone list is served from the static data."""
    status, body = await get_json(webserver_client, "/api/basis/time/timezones?sort=asc")
    assert status == 200
    assert body["code"] == 0
    data = body["data"]
    assert len(data) > 100
    assert {"code", "name", "l3area", "offset"} <= set(data[0])
    assert any(entry["code"] == "Europe/Berlin" for entry in data)
