"""Tests for service and tips endpoints."""

from aiohttp.test_utils import TestClient
import pytest

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_double_slash_service_and_tips_routes(webserver_client: TestClient) -> None:
    """The app's empty account segment is accepted on service and tips routes."""
    responses = {
        "//service/activityList": {"activityList": []},
        "//service/groupList": {"groupList": []},
        "//service/proactiveMessages": {"msgList": [], "hasMore": "N"},
        "//tips/groupList": {"moduleList": []},
        "//tips/tipsList": {"tipsList": []},
    }
    for path, expected in responses.items():
        async with webserver_client.get(f"{_PRIVATE}{path}") as response:
            assert response.status == 200
            assert (await response.json())["data"] == expected
