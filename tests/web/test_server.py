import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.server import WebServer, WebserverBinding
from tests import HOST, WEBSERVER_PORT


async def test_webserver_ssl() -> None:
    webserver = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, True), False)
    await webserver.start()


async def test_webserver_no_ssl() -> None:
    webserver = WebServer(WebserverBinding(HOST, 11112, False), False)
    await webserver.start()


@pytest.mark.usefixtures("clean_database", "xmpp_server", "helper_bot")
async def test_base(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/")
    assert resp.status == 200


# @pytest.mark.usefixtures("clean_database", "xmpp_server", "helper_bot")
# async def test_restart_service(webserver_client: TestClient) -> None:
#     resp = await webserver_client.get("/restart_Helperbot")
#     assert resp.status == 200

#     resp = await webserver_client.get("/restart_MQTTServer")
#     assert resp.status == 200

#     resp = await webserver_client.get("/restart_XMPPServer")
#     assert resp.status == 200


async def test_remove_bot(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/bot/remove/test_did")
    assert resp.status == 200


async def test_remove_client(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/client/remove/test_resource")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database")
async def test_post_lookup(webserver_client: TestClient) -> None:
    # Test FindBest
    postbody = {"todo": "FindBest", "service": "EcoMsgNew"}
    resp = await webserver_client.post("/lookup.do", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    test_resp = json.loads(text)
    assert test_resp["result"] == "ok"

    # Test EcoUpdate
    postbody = {"todo": "FindBest", "service": "EcoUpdate"}
    resp = await webserver_client.post("/lookup.do", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    test_resp = json.loads(text)
    assert test_resp["result"] == "ok"
