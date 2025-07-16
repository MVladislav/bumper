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
    resp = await webserver_client.get("/")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_restart_helperbot(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/restart_Helperbot")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "mqtt_server")
async def test_restart_mqtt_server(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/restart_MQTTServer")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "xmpp_server")
async def test_restart_xmpp_server(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/restart_XMPPServer")
    assert resp.status == 200


async def test_remove_bot(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/bot/remove/test_did")
    assert resp.status == 200


async def test_remove_client(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/client/remove/test_resource")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database")
async def test_post_lookup(webserver_client: TestClient) -> None:
    # Test FindBest
    body = {"todo": "FindBest", "service": "EcoMsgNew"}
    resp = await webserver_client.post("/lookup.do", json=body)
    assert resp.status == 200
    data = await resp.json()
    assert data.get("result") == "ok"

    # Test EcoUpdate
    body = {"todo": "FindBest", "service": "EcoUpdate"}
    resp = await webserver_client.post("/lookup.do", json=body)
    assert resp.status == 200
    data = await resp.json()
    assert data.get("result") == "ok"
