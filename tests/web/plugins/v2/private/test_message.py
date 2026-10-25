"""Tests for bumper/web/plugins/v2/private/message.py."""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_has_more_unread_message_accepts_empty_account_segment(webserver_client: TestClient) -> None:
    """The app uses both populated and empty account path segments."""
    paths = (
        "/v2/private/us/en/dev_1234/global_e/1/0/0/message/hasMoreUnReadMsg",
        "/v2/private/us/en/dev_1234/global_e/1/0/1//message/hasMoreUnReadMsg",
    )
    for path in paths:
        async with webserver_client.get(path) as response:
            assert response.status == 200
            result = await response.json()
            assert result["code"] == "0000"
            assert result["data"] == {"moreUnReadMsg": "N"}
