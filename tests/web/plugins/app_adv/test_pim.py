"""Tests for bumper/web/plugins/app_adv/pim.py"""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_pim_offline(webserver_client: TestClient) -> None:
    """Test /pim/offline.html endpoint."""
    async with webserver_client.get("/app_adv/pim/offline.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert len(text) > 0


@pytest.mark.usefixtures("clean_database")
async def test_pim_network_setup_preparation_by_series(webserver_client: TestClient) -> None:
    """Test /pim/network_setup_preparation_by_series.html endpoint."""
    async with webserver_client.get("/app_adv/pim/network_setup_preparation_by_series.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert text == "🤖"


@pytest.mark.usefixtures("clean_database")
async def test_pim_find_qrcode(webserver_client: TestClient) -> None:
    """Test /pim/find_qrcode.html endpoint."""
    async with webserver_client.get("/app_adv/pim/find_qrcode.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert text == "🤖"


@pytest.mark.usefixtures("clean_database")
async def test_pim_faq_problem_new(webserver_client: TestClient) -> None:
    """Test /pim/faq_problem_new.html endpoint."""
    async with webserver_client.get("/app_adv/pim/faq_problem_new.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert text == "🤖"


@pytest.mark.usefixtures("clean_database")
async def test_pim_active_discovery(webserver_client: TestClient) -> None:
    """Test /pim/active_discovery.html endpoint."""
    async with webserver_client.get("/app_adv/pim/active_discovery.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert text == "🤖"


@pytest.mark.usefixtures("clean_database")
async def test_pim_view_wifi(webserver_client: TestClient) -> None:
    """Test /pim/viewWiFi.html endpoint."""
    async with webserver_client.get("/app_adv/pim/viewWiFi.html") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        text = await resp.text()
        assert text == "🤖"
