"""Tests for the Goat guide pages served by the app_adv plugin."""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
@pytest.mark.parametrize(
    "path",
    [
        "/app_adv/goat/winter_guide.html",
        "/app_adv/goat/maintenance_guide_o_series.html",
        "/app_adv/goat/pin_code_settings.html",
        "/app_adv/goat/rtk.html",
    ],
)
async def test_goat_guide_is_a_document(webserver_client: TestClient, path: str) -> None:
    async with webserver_client.get(path) as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        assert "<!DOCTYPE html>" in await resp.text()
