"""Tests for service and tips endpoints."""

from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json

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
        status, body = await get_json(webserver_client, f"{_PRIVATE}{path}")
        assert status == 200
        assert body["data"] == expected
