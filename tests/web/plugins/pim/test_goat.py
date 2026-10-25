"""Tests for the Goat guide pages served by the pim plugin."""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
@pytest.mark.parametrize(
    "path",
    [
        "/pim/set_pin_code_guide.html",
        "/pim/advanced_features.html",
    ],
)
async def test_goat_guide_is_a_document(webserver_client: TestClient, path: str) -> None:
    async with webserver_client.get(path) as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        assert "<!DOCTYPE html>" in await resp.text()
