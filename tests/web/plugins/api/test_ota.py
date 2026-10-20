"""Tests for the firmware answer of the app (the ota plugin)."""

import base64

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_the_firmware_answer_says_that_there_is_no_update(webserver_client: TestClient) -> None:
    """Bumper does not serve firmware, so the robot keeps the version it has."""
    async with webserver_client.get(
        "/api/ota/products/wukong/class/p95mgv/firmware/latest.json?did=did_1234&ver=1.7.5&module=fw0",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["version"] == "1.7.5"
    assert json_resp["force"] is False
    assert json_resp["fw0"]["version"] == "1.7.5"
    assert json_resp["fw0"]["url"] is None
    # The app reads the change log as base64.
    assert "bumper" in base64.b64decode(json_resp["fw0"]["changeLog"]).decode()
