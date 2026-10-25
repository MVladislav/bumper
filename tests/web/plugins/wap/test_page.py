"""Tests for the page the app opens in its web view."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.utils.settings import config as bumper_isc


@pytest.mark.usefixtures("clean_database")
async def test_page_shows_the_verification_code(webserver_client: TestClient) -> None:
    """The page says which code the account can use, because no mail is sent."""
    async with webserver_client.get("/web/page?no=qp8mz4iv") as response:
        assert response.status == 200
        assert response.content_type == "text/html"
        body = await response.text()
        assert bumper_isc.EMAIL_VERIFY_CODE in body
