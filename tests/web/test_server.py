from pathlib import Path
from unittest.mock import patch

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.server import WebServer, WebserverBinding
from tests import HOST, WEBSERVER_PORT


async def test_webserver_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, True), False)
    await server.start()
    await server.shutdown()
    # await asyncio.sleep(0.1)


async def test_webserver_no_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 1, False), False)
    await server.start()
    await server.shutdown()
    # await asyncio.sleep(0.1)


@pytest.mark.usefixtures("clean_database", "xmpp_server", "helper_bot")
async def test_base(webserver_client: TestClient) -> None:
    async with webserver_client.get("/") as resp:
        assert resp.status == 200


# @pytest.mark.usefixtures("clean_database", "helper_bot")
# async def test_restart_helperbot(webserver_client: TestClient) -> None:
#     async with webserver_client.get("/restart_Helperbot") as resp:
#       assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "mqtt_server")
async def test_restart_mqtt_server(webserver_client: TestClient) -> None:
    async with webserver_client.get("/restart_MQTTServer") as resp:
        assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "xmpp_server")
async def test_restart_xmpp_server(webserver_client: TestClient) -> None:
    async with webserver_client.get("/restart_XMPPServer") as resp:
        assert resp.status == 200


async def test_remove_bot(webserver_client: TestClient) -> None:
    async with webserver_client.get("/bot/remove/test_did") as resp:
        assert resp.status == 200


async def test_remove_client(webserver_client: TestClient) -> None:
    async with webserver_client.get("/client/remove/test_resource") as resp:
        assert resp.status == 200


async def test_remove_user(webserver_client: TestClient) -> None:
    async with webserver_client.get("/user/remove/test_resource") as resp:
        assert resp.status == 200


async def test_handle_partial(webserver_client: TestClient) -> None:
    async with webserver_client.get("/server-status") as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert content_type.startswith("text/html")
        assert resp.content_length > 0
        # assert await resp.read()


async def test_favicon(webserver_client: TestClient) -> None:
    async with webserver_client.get("/favicon.ico") as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert content_type.startswith("image/")
        assert resp.content_length > 0
        # assert await resp.read()


async def test_favicon_missing(
    monkeypatch: pytest.MonkeyPatch,
    webserver_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch("bumper.web.server") as mock_files:
        # Simulate Path that does NOT exist
        fake_path = Path("/tmp/nonexistent.ico")  # noqa: S108
        mock_files.return_value.joinpath.return_value = fake_path
        monkeypatch.setattr(Path, "exists", lambda _: False)

        async with webserver_client.get("/favicon.ico") as resp:
            assert resp.status == 500
            body = await resp.text()
            assert "Internal Server Error" in body
            assert "Favicon not found at" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_post_lookup(webserver_client: TestClient) -> None:
    # Test FindBest
    body = {"todo": "FindBest", "service": "EcoMsgNew"}
    async with webserver_client.post("/lookup.do", json=body) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"

    # Test EcoUpdate
    body = {"todo": "FindBest", "service": "EcoUpdate"}
    async with webserver_client.post("/lookup.do", json=body) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data.get("result") == "ok"
