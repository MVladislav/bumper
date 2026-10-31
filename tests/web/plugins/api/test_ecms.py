"""Tests for bumper/web/plugins/api/ecms.py"""

import logging

from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json


async def test_ad_res(webserver_client: TestClient) -> None:
    status, body = await get_json(webserver_client, "/api/ecms/app/ad/res")
    assert status == 200
    assert body["code"] == 0


async def test_resources_known_location_with_empty_data_does_not_warn(
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`home_manage_intro` is served, and its real answer is an empty list.

    Warning because the payload happens to be empty made a genuine
    unknown-location warning impossible to spot.
    """
    with caplog.at_level(logging.WARNING):
        async with webserver_client.get("/api/ecms/app/resources?locations=home_manage_intro") as resp:
            assert resp.status == 200
            body = await resp.json()

    assert body == {"code": 0, "success": True, "data": [], "message": "success"}
    assert "locations is not know" not in caplog.text


async def test_resources_unknown_location_still_warns(
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The warning must survive for a location we genuinely do not serve."""
    with caplog.at_level(logging.WARNING):
        async with webserver_client.get("/api/ecms/app/resources?locations=definitely_not_a_thing") as resp:
            assert resp.status == 200
            body = await resp.json()

    assert body["data"] == []
    assert "locations is not know :: definitely_not_a_thing" in caplog.text


@pytest.mark.parametrize("location", ["home_manage_intro", "robotui_func_ops", "robot_setting_yiko_ops"])
async def test_known_resource_locations_do_not_warn(
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    location: str,
) -> None:
    """Every location the handler serves must be free of the unknown warning."""
    with caplog.at_level(logging.WARNING):
        async with webserver_client.get(f"/api/ecms/app/resources?locations={location}") as resp:
            assert resp.status == 200
            body = await resp.json()

    assert body["success"] is True
    assert "locations is not know" not in caplog.text


async def test_ad_res_v2(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v2") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_uppercase_v2(webserver_client: TestClient) -> None:
    """The app posts the consumable request to the uppercase path."""
    payload = {
        "uid": "uid_1",
        "tags": ["300lc5"],
        "timeZone": 120,
        "location": ["ad_consumable_list_text", "blade", "heap"],
        "channel": "google_play",
    }
    async with webserver_client.post("/api/ecms/app/ad/res/V2", json=payload) as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_v3(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v3") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_v3_trailing_slash(webserver_client: TestClient) -> None:
    """Some app screens request the v3 list with a trailing slash."""
    async with webserver_client.get("/api/ecms/app/ad/res/v3/") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_unknown_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v4") as resp:
        assert resp.status == 404


async def test_user_theme(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/user/theme") as resp:
        assert resp.status == 200


async def test_bot_image_is_served(webserver_client: TestClient) -> None:
    """The generic bot image is a real jpeg, whatever id the path carries."""
    async with webserver_client.get("/api/ecms/file/get/62206001e50121388401de95") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/jpeg"
        content = await resp.read()

    assert content.startswith(b"\xff\xd8")  # jpeg magic bytes


async def test_hint_answers_false_for_every_code(webserver_client: TestClient) -> None:
    """Every hint code the app asks about comes back disabled."""
    async with webserver_client.get("/api/ecms/app/element/hint?codes=300lc5,4mouui") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["success"] is True
    assert body["data"] == {"300lc5": False, "4mouui": False}


async def test_push_event_acknowledges(webserver_client: TestClient) -> None:
    """A push event with both parameters is acknowledged with `ok`."""
    async with webserver_client.get(
        "/api/ecms/app/push/event?dataCategory=300lc5&resourceId=res_1",
    ) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["success"] is True
    assert body["data"] == "ok"


@pytest.mark.parametrize("query", ["", "?dataCategory=300lc5", "?resourceId=res_1"])
async def test_push_event_without_both_parameters_fails(webserver_client: TestClient, query: str) -> None:
    """A push event missing either parameter fails with the parameter error."""
    async with webserver_client.get(f"/api/ecms/app/push/event{query}") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body == {
        "ret": "fail",
        "todo": "result",
        "code": 500,
        "error": "request params missing: dataCategory or resourceId",
    }


async def test_user_theme_enabled_reports_enabled(webserver_client: TestClient) -> None:
    """The theme is enabled until a caller says otherwise."""
    async with webserver_client.get("/api/ecms/app/user/theme/enabled") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["success"] is True
    assert body["data"] == {"enabled": True}


async def test_user_theme_enabled_put_acknowledges(webserver_client: TestClient) -> None:
    """A PUT of the theme switch is acknowledged without a payload."""
    async with webserver_client.put("/api/ecms/app/user/theme/enabled", json={"enabled": False}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    assert body["success"] is True
    assert "data" not in body
