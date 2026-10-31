"""Tests for the local Ecovacs event detail page."""

from aiohttp.test_utils import TestClient


async def test_eventdetail_shows_known_robot_error(webserver_client: TestClient) -> None:
    """Render Bumper's known mapping for an error URL the app can open."""
    async with webserver_client.get(
        "/api/pim/eventdetail.html?errcode=520&class=300lc5&lang=en&defaultLang=en",
    ) as response:
        body = await response.text()

    assert response.status == 200
    assert "ERROR_TRAPPED" in body
    assert "Trapped (520)" in body
    assert "Free the mower from the obstruction" in body
    assert "300lc5" in body


async def test_eventdetail_keeps_unknown_error_code(webserver_client: TestClient) -> None:
    """Show an unmapped code rather than losing it or failing the page."""
    async with webserver_client.get("/api/pim/eventdetail.html?errcode=98765&class=unknown") as response:
        body = await response.text()

    assert response.status == 200
    assert "Unknown error (98765)" in body
    assert "98765" in body
    assert "not mapped" in body
