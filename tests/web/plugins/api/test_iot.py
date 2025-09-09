import asyncio
import json
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import MQTTHelperBot
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins.api.iot import handle_commands


def async_return(result: dict[str, str]) -> asyncio.Future:
    f = asyncio.Future()
    f.set_result(result)
    return f


@pytest.mark.usefixtures("clean_database")
async def test_devmgr(webserver_client: TestClient, helper_bot: MQTTHelperBot) -> None:
    # Test PollSCResult
    postbody = {"td": "PollSCResult"}
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"

    # Test HasUnreadMsg
    postbody = {"td": "HasUnreadMsg"}
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"
        assert test_resp["unRead"] is False

    # Test BotCommand
    bot_repo.add("sn_1234", "did_1234", "dev_1234", "res_1234", "eco-ng")
    bot_repo.set_mqtt("did_1234", True)
    postbody = {"toId": "did_1234"}
    postbody = {
        "cmdName": "getBattery",
        "payload": {"header": {"pri": "1", "ts": 1744386360.957655, "tzm": 480, "ver": "0.0.50"}},
        "payloadType": "j",
        "td": "q",
        "toId": "did_1234",
        "toRes": "Gy2C",
        "toType": "p95mgv",
    }

    # Test return fail timeout
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "fail"
        assert test_resp["debug"] == "wait for response timed out"

    # Test return get status (NOTE: Fake, not useful, needs to be improved)
    command_getstatus_resp = {
        "id": "resp_1234",
        "resp": "<ctl ret='ok' status='idle'/>",
        "ret": "ok",
    }
    helper_bot.send_command = mock.MagicMock(return_value=async_return(web.json_response(command_getstatus_resp)))
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "ok"


async def test_fails_when_helperbot_is_none(webserver_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bumper_isc, "mqtt_helperbot", None)

    async with webserver_client.post("/api/iot/devmanager.do", json={}) as resp:
        assert resp.status == 200
        body = await resp.json()
        assert body["ret"] == "fail"


async def test_bot_not_found_returns_error(webserver_client: TestClient) -> None:
    postbody = {
        "cmdName": "getBattery",
        "td": "q",
        "toId": "nonexistent",
        "payload": {"header": {"pri": "1"}},
        "payloadType": "j",
        "toRes": "xyz",
        "toType": "p95mgv",
    }
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        body = await resp.json()
        assert body["ret"] == "fail"
        assert "requested bot is not supported" in body["debug"]


async def test_bot_wrong_company(webserver_client: TestClient) -> None:
    bot_repo.add("sn_4321", "did_wrong", "dev", "res", "other-company")
    postbody = {
        "cmdName": "getBattery",
        "td": "q",
        "toId": "did_wrong",
        "payload": {"header": {"pri": "1"}},
        "payloadType": "j",
        "toRes": "xyz",
        "toType": "p95mgv",
    }
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        body = await resp.json()
        assert resp.status == 200
        assert body["ret"] == "fail"
        assert "requested bot is not supported" in body["debug"]


async def test_extended_check_fails_if_not_connected() -> None:
    bot_repo.add("sn_ext", "did_ext", "dev", "res", "eco-ng")
    # MQTT connection NOT set
    postbody = {
        "cmdName": "getBattery",
        "td": "q",
        "toId": "did_ext",
        "payload": {"header": {"pri": "1"}},
        "payloadType": "j",
        "toRes": "xyz",
        "toType": "p95mgv",
    }
    request = mock.MagicMock()
    request.text = mock.AsyncMock(return_value=json.dumps(postbody))
    request.query = {}
    resp = await handle_commands(request, extended_check=True)
    data = json.loads(resp.text)
    assert data["ret"] == "fail"


async def test_td_unknown_logs_warning(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    postbody = {"td": "SomeUnknownTD"}
    with caplog.at_level("WARNING"):
        async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
            assert resp.status == 200
            body = await resp.json()
            assert body["ret"] == "fail"
            assert "TD is not know" in caplog.text
