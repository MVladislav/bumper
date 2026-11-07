import asyncio
import json
import logging
import ssl
import time
from types import SimpleNamespace
from unittest import mock

from aiohttp import web
from aiohttp.test_utils import TestClient
from aiomqtt import Client
import pytest

from bumper import onboarding
from bumper.db import bot_repo, user_repo
from bumper.mqtt.helper_bot import NGIOT_APN_NO_RESPONSE, MQTTHelperBot
from bumper.utils.settings import config as bumper_isc
from bumper.web import payloads
from bumper.web.plugins.api.iot import handle_commands
from bumper.web.static_api import get_product_iot_map
from tests import HOST, MQTT_PORT


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
        "toRes": "res3",
        "toType": "p95mgv",
    }

    # The robot has no broker connection, so the endpoint is offline.
    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        test_resp = await resp.json()
        assert test_resp["ret"] == "fail"
        assert test_resp["errno"] == 4200
        assert test_resp["error"] == "endpoint offline"
        assert "debug" in test_resp

    # Test return get status (NOTE: Fake, not useful, needs to be improved)
    command_getstatus_resp = {
        "id": "resp_1234",
        "resp": "<ctl ret='ok' status='idle'/>",
        "ret": "ok",
    }
    helper_bot.send_command = mock.MagicMock(return_value=async_return(web.json_response(command_getstatus_resp)))
    with mock.patch("bumper.web.plugins.api.iot._bot_mqtt_connected", return_value=True):
        async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
            assert resp.status == 200
            test_resp = await resp.json()
            assert test_resp["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_devmgr_reports_an_offline_robot(webserver_client: TestClient) -> None:
    """An unknown robot is reported as offline.

    `/api/iot/devmanager.do` answers
    `{"ret": "fail", "errno": 4200, "error": "endpoint offline", "debug": …}`.
    An answer of errno 500 after the helper timeout is indistinguishable from a
    broken server to the app, which gives up after 15 seconds.
    """
    bot_repo.add("sn_off", "did_off", "p95mgv", "res1", "eco-ng")
    postbody = {
        "cmdName": "getBattery",
        "payload": {"header": {"pri": "1"}},
        "payloadType": "j",
        "td": "q",
        "toId": "did_off",
        "toRes": "res3",
        "toType": "p95mgv",
    }

    async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["ret"] == "fail"
    assert body["errno"] == 4200
    assert body["error"] == "endpoint offline"
    assert "debug" in body


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_devmgr_times_out_when_the_robot_does_not_answer(
    webserver_client: TestClient,
) -> None:
    """A robot that is on the broker but does not answer is a timeout.

    That is a different condition than an offline robot, and the official
    server does not report it as errno 4200.
    """
    bot_repo.add("sn_slow", "did_slow", "p95mgv", "res1", "eco-ng")
    postbody = {
        "cmdName": "getBattery",
        "payload": {"header": {"pri": "1"}},
        "payloadType": "j",
        "td": "q",
        "toId": "did_slow",
        "toRes": "res3",
        "toType": "p95mgv",
    }

    with mock.patch("bumper.web.plugins.api.iot._bot_mqtt_connected", return_value=True):
        async with webserver_client.post("/api/iot/devmanager.do", json=postbody) as resp:
            assert resp.status == 200
            body = await resp.json()

    assert body["ret"] == "fail"
    assert body["debug"] == "mqtt wait for response failed, see logs form more information"


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
    """The app appends a build tag to `PreWifiConfig`.

    Both the bare command and `PreWifiConfig0306` answer with a flat
    `{"ret":"ok"}` and no warning.
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


@pytest.mark.usefixtures("clean_database")
async def test_wifi_setup_completes_when_the_robot_connects(
    webserver_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The setup poll returns the robot identity after its MQTT login."""
    monkeypatch.setattr(payloads, "get_product_iot_map", get_product_iot_map)
    user_id = "wifi-setup-user"
    sck = "wifi-setup-key"
    bot_name = "t10-robot"
    did = "t10-device-id"
    class_id = "p95mgv"
    resource = "t10-resource"
    user_repo.add(user_id)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PreWifiConfig", "sck": sck, "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200
        assert await resp.json() == {"ret": "ok"}

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": sck, "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200
        pending = await resp.json()
    assert pending["ret"] == "fail"
    assert pending["errno"] == 600
    assert pending["subCode"] == 1
    assert isinstance(pending["debug"], str)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": "different-setup-key", "auth": {"userid": "other-user"}},
    ) as resp:
        assert resp.status == 200
        assert (await resp.json())["ret"] == "fail"

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier=f"{did}@{class_id}/{resource}",
        username=bot_name,
    ) as client:
        await client.publish(f"iot/scsync/{sck}", b"{}", qos=1)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": sck, "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200
        assert await resp.json() == {
            "ret": "ok",
            "did": did,
            "type": class_id,
            "resource": resource,
            "name": bot_name,
        }

    async with webserver_client.post(
        "/api/appsvr/app.do",
        json={"todo": "GetGlobalDeviceList", "userid": user_id},
    ) as resp:
        assert resp.status == 200
        device_list = await resp.json()
    assert device_list["ret"] == "ok"
    assert [device["did"] for device in device_list["devices"]] == [did]


@pytest.mark.usefixtures("clean_database")
async def test_t10_setup_slot_survives_the_observed_app_delay(
    webserver_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A T10 setup survives the 11m34s gap observed before the first poll."""
    clock = [0.0]
    monkeypatch.setattr(onboarding, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    sck = "t10-setup-key-after-delay"

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PreWifiConfig", "sck": sck, "auth": {"userid": "t10-delay-user"}},
    ) as resp:
        assert resp.status == 200

    clock[0] += 11 * 60 + 34
    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": sck, "auth": {"userid": "t10-delay-user"}},
    ) as resp:
        assert (await resp.json())["ret"] == "fail"

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier="t10-after-delay@p95mgv/resource-after-delay",
        username="t10-after-delay",
    ) as client:
        await client.publish(f"iot/scsync/{sck}", b"{}", qos=1)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": sck, "auth": {"userid": "t10-delay-user"}},
    ) as resp:
        result = await resp.json()
    assert result["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_poll_succeeds_when_its_key_differs_from_prewifi_for_the_same_user(
    webserver_client: TestClient,
) -> None:
    """The captured app changes sck between setup start and polling."""
    user_id = "t10-setup-user"
    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PreWifiConfig", "sck": "prewifi-key", "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": "poll-key", "auth": {"userid": user_id}},
    ) as resp:
        assert (await resp.json())["ret"] == "fail"

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier="t10-new-key@p95mgv/resource-new-key",
        username="t10-new-key",
    ) as client:
        async with webserver_client.post(
            "/api/iot/devmanager.do",
            json={"td": "PollSCResult", "sck": "poll-key", "auth": {"userid": user_id}},
        ) as resp:
            assert (await resp.json())["ret"] == "fail"
        await client.publish("iot/scsync/poll-key", b"{}", qos=1)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": "poll-key", "auth": {"userid": "other-user"}},
    ) as resp:
        wrong_user_result = await resp.json()
    assert wrong_user_result["ret"] == "fail"

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": "poll-key", "auth": {"userid": user_id}},
    ) as resp:
        result = await resp.json()
    assert result == {
        "ret": "ok",
        "did": "t10-new-key",
        "type": "p95mgv",
        "resource": "resource-new-key",
        "name": "t10-new-key",
    }


@pytest.mark.usefixtures("clean_database")
async def test_another_mqtt_bot_class_completes_with_its_matching_sync(
    webserver_client: TestClient,
) -> None:
    """The setup protocol is class-agnostic for MQTT bots that send scsync."""
    user_id = "mqtt-setup-user"
    poll_key = "goat-poll-key"
    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PreWifiConfig", "sck": "goat-prewifi-key", "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": poll_key, "auth": {"userid": user_id}},
    ) as resp:
        assert (await resp.json())["ret"] == "fail"

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier="goat-device@300lc5/goat-resource",
        username="goat-robot",
    ) as client:
        async with webserver_client.post(
            "/api/iot/devmanager.do",
            json={"td": "PollSCResult", "sck": poll_key, "auth": {"userid": user_id}},
        ) as resp:
            assert (await resp.json())["ret"] == "fail"
        await client.publish(f"iot/scsync/{poll_key}", b"{}", qos=1)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": poll_key, "auth": {"userid": user_id}},
    ) as resp:
        result = await resp.json()
    assert result == {
        "ret": "ok",
        "did": "goat-device",
        "type": "300lc5",
        "resource": "goat-resource",
        "name": "goat-robot",
    }


@pytest.mark.usefixtures("clean_database")
async def test_sync_sender_identity_wins_over_an_earlier_bot_reconnect(
    webserver_client: TestClient,
) -> None:
    """The matching sync publish identifies the device this setup is adding."""
    user_id = "setup-owner"
    poll_key = "target-poll-key"
    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PreWifiConfig", "sck": "start-key", "auth": {"userid": user_id}},
    ) as resp:
        assert resp.status == 200

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": poll_key, "auth": {"userid": user_id}},
    ) as resp:
        assert (await resp.json())["ret"] == "fail"

    tls_context = ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier="old-device@300lc5/old-resource",
        username="old-robot",
    ):
        pass

    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=tls_context,
        identifier="new-device@300lc5/new-resource",
        username="new-robot",
    ) as client:
        await client.publish(f"iot/scsync/{poll_key}", b"{}", qos=1)

    async with webserver_client.post(
        "/api/iot/devmanager.do",
        json={"td": "PollSCResult", "sck": poll_key, "auth": {"userid": user_id}},
    ) as resp:
        result = await resp.json()

    assert result == {
        "ret": "ok",
        "did": "new-device",
        "type": "300lc5",
        "resource": "new-resource",
        "name": "new-robot",
    }


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
    query = {"si": "si_v2", "ct": "q", "eid": "did_v2", "et": "p95mgv", "er": "res1", "apn": "getPos", "fmt": "j"}
    async with webserver_client.post("/api/iot/endpoint/control/v2", json=postbody, params=query) as resp:
        assert resp.status == 200
        # Unknown bot -> the v8 "not supported" answer, which proves the route
        # resolved rather than 404ing.
        body = await resp.json()
        assert body["ret"] == "fail"
        assert "requested bot is not supported" in body["debug"]


@pytest.mark.usefixtures("clean_database")
async def test_endpoint_control_v2_offline_shape_for_known_bot(webserver_client: TestClient) -> None:
    bot_repo.add("sn_off", "did_off", "p95mgv", "res1", "eco-ng")
    bot_repo.set_mqtt("did_off", False)

    postbody = {"body": {"data": ["deebotPos"]}, "header": {"pri": 2}}
    query = {"si": "si_off2", "ct": "q", "eid": "did_off", "et": "p95mgv", "er": "res1", "apn": "getPos", "fmt": "j"}

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

    bot_repo.add("sn_apping", "did_appping", "p95mgv", "res1", "eco-ng")
    bot_repo.set_mqtt("did_appping", True)

    started = time.monotonic()
    # Report the bot as live so the request reaches the helper bot; the offline
    # fast path has its own tests.
    with mock.patch("bumper.web.plugins.api.iot._bot_mqtt_connected", return_value=True):
        async with webserver_client.post(
            "/api/iot/endpoint/control?si=si_apping&ct=q&eid=did_appping&et=p95mgv&er=res1&apn=appping&fmt=j",
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
    bot_repo.add("sn_offline", "did_nobot", "p95mgv", "res1", "eco-ng")
    bot_repo.set_mqtt("did_nobot", False)

    async with webserver_client.post(
        "/api/iot/endpoint/control?si=si_pos&ct=q&eid=did_nobot&et=p95mgv&er=res1&apn=getPos&fmt=j",
        json={"header": {"pri": 2}},
    ) as resp:
        assert resp.status == 200
        assert resp.headers["x-ngiot-errno"] == "4200"
