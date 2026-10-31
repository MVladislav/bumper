"""Tests for bumper/web/plugins/v1/private/member.py."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.envelope import RETURN_API_SUCCESS
from tests.web.helpers import get_json

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


def _assert_scene(client_result: dict, get_point: int | None, prompt: str | None) -> None:
    assert client_result["code"] == RETURN_API_SUCCESS
    entry = client_result["data"]["completeList"][0]
    assert entry["getExp"] == 0
    assert entry["getPoint"] == get_point
    assert entry["onlyOnce"] == "N"
    assert entry["prompt"] == prompt


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_suction(webserver_client: TestClient) -> None:
    status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/member/getExpByScene?scene=GLOBALAPP_REGULATE_DEEBOT_SUCTION",
    )
    assert status == 200
    _assert_scene(result, 0, "Task DEEBOT Perform suction power setting, +0")


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_water(webserver_client: TestClient) -> None:
    status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/member/getExpByScene?scene=GLOBALAPP_REGULATE_DEEBOT_WATER",
    )
    assert status == 200
    _assert_scene(result, 0, "Perform task DEEBOT water flow rate, +0")


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_consumables(webserver_client: TestClient) -> None:
    status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/member/getExpByScene?scene=GLOBALAPP_TIMING_OF_CONSUMABLES",
    )
    assert status == 200
    _assert_scene(result, 0, "Perform Display accessory usage task, +0")


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_virtual_wall(webserver_client: TestClient) -> None:
    status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/member/getExpByScene?scene=GLOBALAPP_VIRTUAL_WALL_MANAGEMENT",
    )
    assert status == 200
    _assert_scene(result, 0, "Perform task Manage DEEBOT Virtual Walls, +0")


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_rename_list(webserver_client: TestClient) -> None:
    for scene in [
        "GLOBALAPP_MACHINE_RENAME",
        "GLOBALAPP_AREA_CATE_RENAME",
        "GLOBALAPP_FIRST_SET_PERSONAL_CLEAN_MODULE",
        "GLOBALAPP_SHOW_CLEAN_LOG",
        "GLOBALAPP_USE_HELP_CENTER",
        "GLOBALAPP_USE_SIDE_FILTER",
    ]:
        status, result = await get_json(
            webserver_client,
            f"{_PRIVATE}/member/getExpByScene?scene={scene}",
        )
        assert status == 200
        _assert_scene(result, 0, ":P, +0")


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_unknown(webserver_client: TestClient) -> None:
    status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/member/getExpByScene?scene=UNKNOWN_SCENE",
    )
    assert status == 200
    _assert_scene(result, None, None)


@pytest.mark.usefixtures("clean_database")
async def test_get_exp_by_scene_default(webserver_client: TestClient) -> None:
    status, result = await get_json(webserver_client, f"{_PRIVATE}/member/getExpByScene")
    assert status == 200
    _assert_scene(result, None, None)
