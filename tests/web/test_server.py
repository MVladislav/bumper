import json

import pytest

from bumper.utils.settings import config as bumper_isc
from bumper.web.server import WebServer, WebserverBinding
from bumper.xmpp.xmpp import XMPPServer
from tests import HOST, WEBSERVER_PORT


async def test_webserver_ssl() -> None:
    webserver = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, True), False)
    await webserver.start()


async def test_webserver_no_ssl() -> None:
    webserver = WebServer(WebserverBinding(HOST, 11112, False), False)
    await webserver.start()


@pytest.mark.usefixtures("helper_bot", "clean_database")
async def test_base(webserver_client) -> None:
    # Start XMPP
    xmpp_server = XMPPServer(HOST, 5223)
    bumper_isc.xmpp_server = xmpp_server
    await xmpp_server.start_async_server()

    resp = await webserver_client.get("/")
    assert resp.status == 200

    await bumper_isc.xmpp_server.disconnect()


@pytest.mark.usefixtures("helper_bot", "clean_database")
async def test_restartService(webserver_client) -> None:
    # Start XMPP
    xmpp_server = XMPPServer(HOST, 5223)
    bumper_isc.xmpp_server = xmpp_server
    await xmpp_server.start_async_server()

    resp = await webserver_client.get("/restart_Helperbot")
    assert resp.status == 200

    # resp = await webserver_client.get("/restart_MQTTServer")
    # assert resp.status == 200

    resp = await webserver_client.get("/restart_XMPPServer")
    assert resp.status == 200

    await xmpp_server.disconnect()


async def test_RemoveBot(webserver_client) -> None:
    resp = await webserver_client.get("/bot/remove/test_did")
    assert resp.status == 200


async def test_RemoveClient(webserver_client) -> None:
    resp = await webserver_client.get("/client/remove/test_resource")
    assert resp.status == 200


@pytest.mark.usefixtures("clean_database")
async def test_postLookup(webserver_client) -> None:
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
