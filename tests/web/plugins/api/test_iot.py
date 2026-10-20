import asyncio
import json
import logging
import time
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import NGIOT_APN_NO_RESPONSE, MQTTHelperBot
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
        assert test_resp["debug"] == "mqtt wait for response failed, see logs form more information"

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


async def test_pre_wifi_config_with_build_tag(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """The app appends a build tag: `PreWifiConfig0306` was seen in the field.

    Exact-match only meant a spurious "TD is not know" warning on every wifi
    setup. The captures only show the bare `PreWifiConfig`, and both answer
    with a flat `{"ret":"ok"}`.
    """
    with caplog.at_level(logging.WARNING):
        async with webserver_client.post("/api/iot/devmanager.do", json={"td": "PreWifiConfig0306"}) as resp:
            assert resp.status == 200
            body = await resp.json()

    assert body == {"ret": "ok"}
    assert "TD is not know" not in caplog.text


async def test_pre_wifi_config_plain(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/iot/devmanager.do", json={"td": "PreWifiConfig"}) as resp:
        assert resp.status == 200
        assert (await resp.json()) == {"ret": "ok"}


async def test_td_unknown_logs_warning(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    postbody = {"td": "SomeUnknownTD"}
    with caplog.at_level("WARNING"):
        async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
            assert resp.status == 200
            body = await resp.json()
            assert body["ret"] == "fail"
            assert "TD is not know" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_endpoint_control_v2_is_routed(webserver_client: TestClient) -> None:
    postbody = {"body": {"data": []}, "header": {"pri": 2}}
    query = {"si": "si_v2", "ct": "q", "eid": "did_v2", "et": "p95mgv", "er": "rljY", "apn": "getPos", "fmt": "j"}
    async with webserver_client.post("/api/iot/endpoint/control/v2", json=postbody, params=query) as resp:
        assert resp.status == 200
        # Unknown bot -> the v8 "not supported" answer, which proves the route
        # resolved rather than 404ing.
        body = await resp.json()
        assert body["ret"] == "fail"
        assert "requested bot is not supported" in body["debug"]


@pytest.mark.usefixtures("clean_database")
async def test_endpoint_control_v2_offline_shape_for_known_bot(webserver_client: TestClient) -> None:
    bot_repo.add("sn_off", "did_off", "p95mgv", "rljY", "eco-ng")
    bot_repo.set_mqtt("did_off", False)

    postbody = {"body": {"data": ["deebotPos"]}, "header": {"pri": 2}}
    query = {"si": "si_off2", "ct": "q", "eid": "did_off", "et": "p95mgv", "er": "rljY", "apn": "getPos", "fmt": "j"}

    with mock.patch("bumper.web.plugins.api.iot._bot_mqtt_connected", return_value=False):
        async with webserver_client.post("/api/iot/endpoint/control/v2", json=postbody, params=query) as resp:
            assert resp.status == 200
            assert resp.headers["x-ngiot-errno"] == "4200"
            assert await resp.read() == b""


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_appping_does_not_wait_for_a_response(webserver_client: TestClient) -> None:
    """`appping` is a keepalive the app abandons immediately.

    All 16 occurrences across the eight transcripts end in
    `stream reset by client (CANCEL)`; the app waits ~28 s between them. Bumper
    must acknowledge without publishing a pending command, or it pins an HTTP
    handler and a pending-command entry for the full helper timeout, ~128 times
    an hour.
    """
    assert "appping" in NGIOT_APN_NO_RESPONSE

    bot_repo.add("sn_apping", "did_appping", "p95mgv", "rljY", "eco-ng")
    bot_repo.set_mqtt("did_appping", True)

    started = time.monotonic()
    # Report the bot as live so the request reaches the helper bot; the offline
    # fast path has its own tests.
    with mock.patch("bumper.web.plugins.api.iot._bot_mqtt_connected", return_value=True):
        async with webserver_client.post(
            "/api/iot/endpoint/control?si=si_apping&ct=q&eid=did_appping&et=p95mgv&er=rljY&apn=appping&fmt=j",
            json={"header": {"pri": 2}},
        ) as resp:
            assert resp.status == 200
            body = json.loads(await resp.read())
    elapsed = time.monotonic() - started

    # The helper bot's default timeout is 60 s; a blocking implementation would
    # either sit on that or be cut off by the app's 15 s HTTP timeout.
    assert elapsed < 5, f"appping blocked for {elapsed:.1f}s"
    assert body["body"]["code"] == 0


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_normal_command_still_waits(webserver_client: TestClient) -> None:
    """Only the known fire-and-forget names skip the wait.

    A registered but disconnected bot takes the offline path, which is the proof
    that the no-wait list did not swallow ordinary commands.
    """
    bot_repo.add("sn_offline", "did_nobot", "p95mgv", "rljY", "eco-ng")
    bot_repo.set_mqtt("did_nobot", False)

    async with webserver_client.post(
        "/api/iot/endpoint/control?si=si_pos&ct=q&eid=did_nobot&et=p95mgv&er=rljY&apn=getPos&fmt=j",
        json={"header": {"pri": 2}},
    ) as resp:
        assert resp.status == 200
        assert resp.headers["x-ngiot-errno"] == "4200"
