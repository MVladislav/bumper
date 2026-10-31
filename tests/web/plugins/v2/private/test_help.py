"""Tests for bumper/web/plugins/v2/private/help.py."""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_get_help_index(webserver_client: TestClient) -> None:
    """The v2 help endpoint returns the help index."""
    async with webserver_client.get("/v2/private/us/en/dev_1234/global_e/1/0/0/help/getHelpIndex") as response:
        assert response.status == 200
        result = await response.json()
        assert result["code"] == "0000"
        assert isinstance(result["data"]["indexProductList"], list)
        assert isinstance(result["data"]["moreHelpModuleList"], list)
