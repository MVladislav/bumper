import asyncio
import json
import time

from aiomqtt import Client, Topic
import pytest
from testfixtures import LogCapture

from bumper.db import bot_repo, clean_log_repo
from bumper.mqtt.helper_bot import CommandDto, MQTTCommandModel, MQTTHelperBot, _fw_ver_of
from bumper.mqtt.server import MQTTServer
from bumper.utils.device_error_handler import discard_device_error_report, get_device_error_report
from tests import HOST, MQTT_PORT


def test_mqtt_command_model_version_1() -> None:
    cmdjson = {
        "payloadType": "j",
        "toId": "did_123",
        "toType": "ls1ok3",
        "toRes": "res_123",
        "td": "test_td",
        "cmdName": "clean_V2",
        "payload": {"key": "value"},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_OLD)
    assert cmd.version == MQTTCommandModel.VERSION_OLD
    assert cmd.did == "did_123"
    assert cmd.to_type == "ls1ok3"
    assert cmd.to_res == "res_123"
    assert cmd.td == "test_td"
    assert cmd.cmd_name == "clean_V2"
    assert cmd.payload == '{"key": "value"}'
    assert cmd.payload_type == "j"


def test_mqtt_command_model_version_2() -> None:
    cmdjson = {
        "fmt": "j",
        "apn": "getStats",
        "eid": "did_456",
        "et": "ls1ok3",
        "er": "res_456",
        "ct": "test_ct",
        "payload": {"header": {"pri": 1}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    assert cmd.version == MQTTCommandModel.VERSION_NEW
    assert cmd.did == "did_456"
    assert cmd.to_type == "ls1ok3"
    assert cmd.to_res == "res_456"
    assert cmd.td == "test_ct"
    assert cmd.cmd_name == "getStats"
    assert cmd.payload == '{"header": {"pri": 1}}'
    assert cmd.payload_type == "j"


def test_mqtt_command_model_version_p2p() -> None:
    cmdjson = {
        "cmd": "clean",
        "did": "did_789",
        "mid": "ls1ok3",
        "res": "res_789",
        "data": {"act": "s"},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)
    assert cmd.version == MQTTCommandModel.VERSION_P2P
    assert cmd.did == "did_789"
    assert cmd.to_type == "ls1ok3"
    assert cmd.to_res == "res_789"
    assert cmd.cmd_name == "clean"
    assert cmd.cmd_name_orig == "clean"
    assert cmd.payload == '{"body": {"data": {"act": "start"}}}'  # act: s -> start
    assert cmd.payload_type == "j"

    cmdjson = {
        "cmd": "getBatteryInfo",
        "did": "did_789",
        "mid": "ls1ok3",
        "res": "res_789",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)
    assert cmd.version == MQTTCommandModel.VERSION_P2P
    assert cmd.did == "did_789"
    assert cmd.to_type == "ls1ok3"
    assert cmd.to_res == "res_789"
    assert cmd.cmd_name == "getBattery"  # getBatteryInfo -> getBattery
    assert cmd.cmd_name_orig == "getBatteryInfo"
    assert cmd.payload == '{"body": {"data": {}}}'
    assert cmd.payload_type == "j"


def test_mqtt_command_model_create_topic() -> None:
    cmdjson = {
        "cmd": "getBattery",
        "did": "did_topic",
        "mid": "ls1ok3",
        "res": "res_topic",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)
    topic = cmd.create_topic()
    assert topic == f"iot/p2p/getBattery/helperbot/bumper/helperbot/did_topic/ls1ok3/res_topic/q/{cmd.request_id}/j"


@pytest.mark.usefixtures("mqtt_client")
async def test_helperbot_connect(mqtt_server: MQTTServer) -> None:
    mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
    try:
        await mqtt_helperbot.start()
        assert await mqtt_helperbot.is_connected
    finally:
        await mqtt_helperbot.disconnect()
        assert not await mqtt_helperbot.is_connected
        assert mqtt_helperbot._client is None
        assert mqtt_helperbot._mqtt_task is None
        assert all(session.client_id != "helperbot@bumper/helperbot" for session in mqtt_server.sessions)


@pytest.mark.usefixtures("mqtt_client")
async def test_publish_not_connected(helper_bot: MQTTHelperBot) -> None:
    helper_bot._client = None
    with pytest.raises(Exception, match="MQTT client is not connected"):
        await helper_bot.publish("test/topic", "test_payload")


@pytest.mark.usefixtures("mqtt_client")
async def test_subscribe_topics_not_connected(helper_bot: MQTTHelperBot) -> None:
    helper_bot._client = None
    with pytest.raises(Exception, match="MQTT client is not connected"):
        await helper_bot._subscribe_topics()


async def test_helperbot_message(mqtt_client: Client) -> None:
    with LogCapture() as log:
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        try:
            await mqtt_helperbot.start()
            assert await mqtt_helperbot.is_connected

            # Test broadcast message
            msg_payload = "<ctl ts='1547822804960' td='DustCaseST' st='0'/>"
            msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/res2/x"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Broadcast :: Topic: iot/atr/DustCaseST/bot_serial/ls1ok3/res2/x"
                        " :: Message: <ctl ts='1547822804960' td='DustCaseST' st='0'/>"
                    ),
                ),
            )  # Check broadcast message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()

        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        try:
            await mqtt_helperbot.start()
            assert await mqtt_helperbot.is_connected

            # Send command to bot
            msg_payload = "{}"
            msg_topic_name = "iot/p2p/GetWKVer/helperbot/bumper/helperbot/bot_serial/ls1ok3/res2/q/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Send Command :: Topic: iot/p2p/GetWKVer/helperbot/bumper/helperbot/bot_serial/ls1ok3/res2/q/iCmuqp/j"
                        " :: Message: {}"
                    ),
                ),
            )  # Check send command message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()

        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        try:
            await mqtt_helperbot.start()
            assert await mqtt_helperbot.is_connected

            # Received response to command
            msg_payload = '{"ret":"ok","ver":"0.13.5"}'
            msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Response"
                        " :: Topic: iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/iCmuqp/j"
                        ' :: Message: {"ret":"ok","ver":"0.13.5"}'
                    ),
                ),
            )  # Check received response message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()

        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        try:
            await mqtt_helperbot.start()
            assert await mqtt_helperbot.is_connected

            # Received unknown message
            msg_payload = "test"
            msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/TESTBAD/bumper/helperbot/p/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.2)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Message :: Topic: iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/TESTBAD/bumper/helperbot/p/iCmuqp/j"
                        " :: Message: test"
                    ),
                ),
            )  # Check received message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()

        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        try:
            await mqtt_helperbot.start()
            assert await mqtt_helperbot.is_connected

            # Received error message
            msg_payload = "<ctl ts='1560904925396' td='errors' old='' new='110'/>"
            msg_topic_name = "iot/atr/errors/bot_serial/ls1ok3/res2/x"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Broadcast :: Topic: iot/atr/errors/bot_serial/ls1ok3/res2/x"
                        " :: Message: <ctl ts='1560904925396' td='errors' old='' new='110'/>"
                    ),
                ),
            )  # Check received message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()


@pytest.mark.usefixtures("helper_bot")
async def test_mqtt_error_broadcast_updates_runtime_error_state(mqtt_client: Client) -> None:
    """Keep a broker-visible error broadcast available during this process."""
    discard_device_error_report("bot_serial")
    payload = "<ctl ts='1560904925396' td='errors' old='' new='110'/>"

    try:
        await mqtt_client.publish("iot/atr/errors/bot_serial/ls1ok3/res2/x", payload.encode())
        await asyncio.sleep(0.1)

        report = get_device_error_report("bot_serial")
        assert report is not None
        assert report.codes == (110,)
        assert report.reported_at == 1560904925396
        assert report.source == "mqtt"
    finally:
        discard_device_error_report("bot_serial")


@pytest.mark.usefixtures("clean_database")
async def test_ngiot_get_info_response_records_nested_get_error() -> None:
    """Record nested getError data where firmware versions are remembered."""
    did = "ngiot-error-did"
    discard_device_error_report(did)
    bot_repo.add("serial_ngiot", did, "300lc5", "resource", "eco-ng")
    helper = MQTTHelperBot(HOST, MQTT_PORT, True)
    request_id = "getError"
    helper._commands[request_id] = CommandDto("j", did)
    topic = Topic(f"iot/p2p/getInfo/{did}/300lc5/resource/helperbot/bumper/helperbot/p/{request_id}/j")
    payload = (
        b'{"header":{"tzm":60,"ts":"1793456317228356743","fwVer":"1.11.23"},'
        b'"body":{"code":0,"msg":"ok","data":{"getError":{"code":0,"msg":"ok","data":{"code":[520]}}}}}'
    )
    try:
        await helper._on_message(topic, payload)
        report = get_device_error_report(did)
        assert report is not None
        assert report.codes == (520,)
        assert report.source == "mqtt-p2p"
        assert bot_repo.get(did).fw_ver == "1.11.23"
    finally:
        discard_device_error_report(did)


async def test_helperbot_expire_message(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    expire_msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    expire_msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/testgood/j"
    currenttime = time.time()
    request_id = "ABC"
    data = {
        "time": currenttime,
        "topic": expire_msg_topic_name,
        "payload": expire_msg_payload,
    }

    helper_bot._commands[request_id] = data

    assert helper_bot._commands[request_id] == data

    await asyncio.sleep(0.1)
    msg_payload = "<ctl ts='1547822804960' td='DustCaseST' st='0'/>"
    msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/res2/x"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())  # Send another message to force get_msg

    await asyncio.sleep(0.1 * 2)

    assert helper_bot._commands.get(request_id, None) is None


async def test_helperbot_send_command(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    cmdjson = {
        "toType": "ls1ok3",
        "payloadType": "j",
        "toRes": "res2",
        "payload": {},
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "GetWKVer",
        "auth": {
            "token": "us_00000000000000000000000000000000",
            "resource": "IOSF00000001",
            "userid": "testuser",
            "with": "users",
            "realm": "ecouser.net",
        },
    }
    cmd = MQTTCommandModel(cmdjson)
    cmd.request_id = "testfail"
    commandresult = await helper_bot.send_command(cmd)
    # Don't send a response, ensure timeout
    assert json.loads(commandresult.body.decode("utf-8")) == {
        "id": "testfail",
        "errno": 500,
        "ret": "fail",
        "debug": "mqtt wait for response failed, see logs form more information",
    }  # Check timeout

    # Send response beforehand
    msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/testgood/j"
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(asyncio.create_task, mqtt_client.publish(msg_topic_name, msg_payload.encode()))

    cmd = MQTTCommandModel(cmdjson)
    cmd.request_id = "testgood"
    commandresult = await helper_bot.send_command(cmd)
    assert json.loads(commandresult.body.decode("utf-8")) == {
        "id": "testgood",
        "resp": {"ret": "ok", "ver": "0.13.5"},
        "ret": "ok",
        "payloadType": "j",
    }

    # Test GetLifeSpan (xml command)
    cmdjson = {
        "toType": "ls1ok3",
        "payloadType": "x",
        "toRes": "res2",
        "payload": '<ctl type="Brush"/>',
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "GetLifeSpan",
        "auth": {
            "token": "us_00000000000000000000000000000000",
            "resource": "IOSF00000001",
            "userid": "testuser",
            "with": "users",
            "realm": "ecouser.net",
        },
    }

    # Send response beforehand
    msg_payload = "<ctl ret='ok' type='Brush' left='4142' total='18000'/>"
    msg_topic_name = "iot/p2p/GetLifeSpan/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/testx/q"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    cmd = MQTTCommandModel(cmdjson)
    cmd.request_id = "testx"
    commandresult = await helper_bot.send_command(cmd)
    assert json.loads(commandresult.body.decode("utf-8")) == {
        "id": "testx",
        "resp": "<ctl ret='ok' type='Brush' left='4142' total='18000'/>",
        "ret": "ok",
        "payloadType": "x",
    }

    # Test json payload (OZMO950)
    cmdjson = {
        "toType": "ls1ok3",
        "payloadType": "j",
        "toRes": "res2",
        "payload": {"header": {"pri": 1, "ts": "1569380075887", "tzm": -240, "ver": "0.0.50"}},
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "getStats",
        "auth": {
            "token": "us_00000000000000000000000000000000",
            "resource": "IOSF00000001",
            "userid": "testuser",
            "with": "users",
            "realm": "ecouser.net",
        },
    }

    # Send response beforehand
    msg_payload = (
        '{"body":{"code":0,"data":{"area":0,"cid":"111","start":"1569378657","time":6,"type":"auto"},"msg":"ok"}'
        ',"header":{"fwVer":"1.6.4","hwVer":"0.1.1","pri":1,"ts":"1569380074036","tzm":480,"ver":"0.0.1"}}'
    )

    msg_topic_name = "iot/p2p/getStats/bot_serial/ls1ok3/res2/helperbot/bumper/helperbot/p/testj/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    cmd = MQTTCommandModel(cmdjson)
    cmd.request_id = "testj"
    commandresult = await helper_bot.send_command(cmd)
    assert json.loads(commandresult.body.decode("utf-8")) == {
        "id": "testj",
        "payloadType": "j",
        "resp": {
            "body": {
                "code": 0,
                "data": {
                    "area": 0,
                    "cid": "111",
                    "start": "1569378657",
                    "time": 6,
                    "type": "auto",
                },
                "msg": "ok",
            },
            "header": {
                "fwVer": "1.6.4",
                "hwVer": "0.1.1",
                "pri": 1,
                "ts": "1569380074036",
                "tzm": 480,
                "ver": "0.0.1",
            },
        },
        "ret": "ok",
    }


@pytest.mark.usefixtures("mqtt_client")
async def test_helperbot_send_command_plain_timeout(helper_bot: MQTTHelperBot) -> None:
    cmdjson = {
        "cmd": "getBattery",
        "did": "did_timeout",
        "mid": "ls1ok3",
        "res": "res_timeout",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)
    helper_bot._timeout = 0.1
    # Do not send a response, so it times out
    result = await helper_bot.send_command_plain(cmd)
    assert result is None


async def test_helperbot_send_command_plain_valid_response(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    helper_bot._timeout = 1
    cmdjson = {
        "cmd": "getBattery",
        "did": "did_valid",
        "mid": "ls1ok3",
        "res": "res_valid",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    # Start a task to send the command
    send_task = asyncio.create_task(helper_bot.send_command_plain(cmd))
    await asyncio.sleep(0)

    # Publish the response to a topic where the request_id is at index 10
    msg_payload = '{"body": {"data": {"value": 80}}}'
    msg_topic_name = f"iot/p2p/getBattery/did_valid/ls1ok3/res_valid/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    # Wait for the response
    result = await send_task
    assert result == {"body": {"data": {"value": 80}}}


async def test_helperbot_send_command_old(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    helper_bot._timeout = 1
    cmdjson = {
        "payloadType": "j",
        "toId": "did_old",
        "toType": "ls1ok3",
        "toRes": "res_old",
        "td": "test_td",
        "cmdName": "GetWKVer",
        "payload": {"key": "value"},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_OLD)

    send_task = asyncio.create_task(helper_bot._send_command_old(cmd))
    await asyncio.sleep(0)

    msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    msg_topic_name = f"iot/p2p/GetWKVer/did_old/ls1ok3/res_old/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["resp"] == {"ret": "ok", "ver": "0.13.5"}


async def test_helperbot_send_command_new(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    helper_bot._timeout = 1
    cmdjson = {
        "fmt": "j",
        "apn": "getStats",
        "eid": "did_new",
        "et": "ls1ok3",
        "er": "res_new",
        "ct": "test_ct",
        "payload": {"header": {"pri": 1}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)

    send_task = asyncio.create_task(helper_bot._send_command_new(cmd))
    await asyncio.sleep(0)

    msg_payload = '{"body": {"data": {"area": 0}}}'
    msg_topic_name = f"iot/p2p/getStats/did_new/ls1ok3/res_new/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    assert result.content_type == "application/octet-stream"
    assert result.headers["x-ngiot-fmt"] == "b"
    assert result.headers["x-ngiot-ret"] == "ok"
    body = json.loads(result.text)
    assert body == {"body": {"data": {"area": 0}}}


async def test_helperbot_send_command_p2p_get_battery(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    helper_bot._timeout = 1
    cmdjson = {
        "cmd": "getBatteryInfo",
        "did": "did_battery",
        "mid": "ls1ok3",
        "res": "res_battery",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))
    await asyncio.sleep(0)

    msg_payload = '{"body": {"data": {"value": 90}}}'
    msg_topic_name = f"iot/p2p/getBattery/did_battery/ls1ok3/res_battery/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["data"]["getBatteryInfo"]["ret"] == "ok"
    assert json_resp["data"]["getBatteryInfo"]["did"] == "did_battery"
    assert json_resp["data"]["getBatteryInfo"]["power"] == 90


async def test_helperbot_send_command_p2p_get_charge_state(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    helper_bot._timeout = 1
    cmdjson = {
        "cmd": "getChargeState",
        "did": "did_charge",
        "mid": "ls1ok3",
        "res": "res_charge",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))
    await asyncio.sleep(0)

    msg_payload = '{"body": {"data": {"isCharging": 1}}}'
    msg_topic_name = f"iot/p2p/getChargeState/did_charge/ls1ok3/res_charge/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["data"]["getChargeState"]["ret"] == "ok"
    assert json_resp["data"]["getChargeState"]["did"] == "did_charge"
    assert json_resp["data"]["getChargeState"]["type"] == "SlotCharging"


async def test_helperbot_send_command_p2p_preserves_generic_command_data(
    mqtt_client: Client,
    helper_bot: MQTTHelperBot,
) -> None:
    """Legacy commands without custom projections must not lose their data."""
    helper_bot._timeout = 1
    cmdjson = {
        "cmd": "getBindToken",
        "did": "did_bind_token",
        "mid": "ls1ok3",
        "res": "res_bind_token",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)
    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))
    await asyncio.sleep(0)

    msg_payload = (
        '{"body":{"data":{"region":"eu-central-1","channel":"production-did_bind_token",'
        '"credentials":{"AccessKeyId":"ASIAexample","TtlSec":3600}}}}'
    )
    msg_topic_name = f"iot/p2p/getBindToken/did_bind_token/ls1ok3/res_bind_token/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    command_data = json_resp["data"]["getBindToken"]
    assert command_data["ret"] == "ok"
    assert command_data["did"] == "did_bind_token"
    assert command_data["region"] == "eu-central-1"
    assert command_data["channel"] == "production-did_bind_token"
    assert command_data["credentials"] == {"AccessKeyId": "ASIAexample", "TtlSec": 3600}


async def test_helperbot_send_command_p2p_charge(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    """Handle a charge reply without relying on the fixture's short timeout."""
    helper_bot._timeout = 1
    cmdjson = {
        "cmd": "charge",
        "did": "did_charge_cmd",
        "mid": "ls1ok3",
        "res": "res_charge_cmd",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))
    await asyncio.sleep(0)

    msg_payload = '{"body": {"msg": "ok"}}'
    msg_topic_name = f"iot/p2p/charge/did_charge_cmd/ls1ok3/res_charge_cmd/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["data"]["charge"]["ret"] == "ok"
    assert json_resp["data"]["charge"]["did"] == "did_charge_cmd"


def test_version_2_adopts_si_as_request_id() -> None:
    cmdjson = {
        "fmt": "j",
        "apn": "getPos",
        "eid": "did_1",
        "et": "p95mgv",
        "er": "res1",
        "ct": "q",
        "si": "LaxGMMNuGoCFgnnJ",
        "payload": {"body": {"data": ["chargePos", "deebotPos"]}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    assert cmd.request_id == "LaxGMMNuGoCFgnnJ"


def test_version_2_generates_request_id_without_si() -> None:
    cmdjson = {
        "fmt": "j",
        "apn": "getPos",
        "eid": "did_1",
        "et": "p95mgv",
        "er": "res1",
        "ct": "q",
        "payload": {"body": {"data": []}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    # Falls back to the generated id rather than an empty string, which would
    # otherwise collapse every pending command onto one cache key.
    assert cmd.request_id != ""
    assert len(cmd.request_id) == 4


def test_request_id_cannot_inject_a_topic_level() -> None:
    """A caller-supplied si must never be able to reshape the MQTT topic."""
    cmdjson = {
        "fmt": "j",
        "apn": "getPos",
        "eid": "did_1",
        "et": "p95mgv",
        "er": "res1",
        "ct": "q",
        "si": "evil/../../other/topic",
        "payload": {"body": {"data": []}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    assert cmd.request_id != "evil/../../other/topic"
    assert "/" not in cmd.request_id


def test_non_string_si_is_ignored() -> None:
    cmdjson = {
        "fmt": "j",
        "apn": "getPos",
        "eid": "did_1",
        "et": "p95mgv",
        "er": "res1",
        "ct": "q",
        "si": 1234,
        "payload": {"body": {"data": []}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    assert len(cmd.request_id) == 4


def test_oversized_si_is_ignored() -> None:
    cmdjson = {
        "fmt": "j",
        "apn": "getPos",
        "eid": "did_1",
        "et": "p95mgv",
        "er": "res1",
        "ct": "q",
        "si": "a" * 200,
        "payload": {"body": {"data": []}},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_NEW)
    assert len(cmd.request_id) == 4


def _decode(response: object) -> dict[str, object]:
    """Return the JSON body of a response as a dict."""
    body = getattr(response, "body", None)
    if body in (None, b""):
        return {}
    return json.loads(body)


@pytest.mark.usefixtures("mqtt_client")
async def test_send_command_new_offline_returns_ngiot_offline(helper_bot: object) -> None:
    cmd = MQTTCommandModel(
        {
            "fmt": "j",
            "apn": "getPos",
            "eid": "did_offline",
            "et": "p95mgv",
            "er": "res1",
            "ct": "q",
            "si": "si_offline",
            "payload": {"body": {"data": []}},
        },
        version=MQTTCommandModel.VERSION_NEW,
    )
    # No robot on the broker answers, so the helper bot times out with None.
    helper_bot._timeout = 0.1
    response = await helper_bot.send_command(cmd)

    assert response.status == 200
    assert response.headers["x-ngiot-errno"] == "4200"
    assert response.headers["x-ngiot-ret"] == "error"
    assert response.headers["X-ECO-REQUEST-ID"] == "si_offline"
    assert response.body == b""


@pytest.mark.usefixtures("mqtt_client")
async def test_send_command_new_fire_and_forget_does_not_wait(helper_bot: object) -> None:
    """`ct=m` must be acknowledged without waiting for the robot."""
    cmd = MQTTCommandModel(
        {
            "fmt": "j",
            "apn": "setChargePos",
            "eid": "did_ff",
            "et": "p95mgv",
            "er": "res1",
            "ct": "m",
            "si": "si_ff",
            "payload": {"body": {"data": {}}},
        },
        version=MQTTCommandModel.VERSION_NEW,
    )
    # A long timeout that the fire-and-forget path must never reach.
    helper_bot._timeout = 30
    response = await helper_bot.send_command(cmd)

    assert response.status == 200
    assert response.headers["x-ngiot-ret"] == "ok"
    assert response.headers["X-ECO-REQUEST-ID"] == "si_ff"
    assert _decode(response)["body"]["code"] == 0


@pytest.mark.usefixtures("mqtt_client")
async def test_send_command_new_rejects_wrong_version(helper_bot: object) -> None:
    cmd = MQTTCommandModel(
        {"toId": "did_x", "cmdName": "getBattery", "payload": {}, "payloadType": "j"},
        version=MQTTCommandModel.VERSION_OLD,
    )
    response = await helper_bot.send_command(cmd)
    assert _decode(response)["ret"] == "fail"


def test_the_firmware_version_is_read_from_the_header_of_the_answer() -> None:
    """The header of an answer of a robot carries the version it runs."""
    payload = json.dumps({"header": {"fwVer": "1.0.0", "hwVer": "2.0.0", "ts": "123"}, "body": {}})
    assert _fw_ver_of(payload) == "1.0.0"

    # An answer without a header, or with a header without the version.
    assert _fw_ver_of(json.dumps({"body": {"data": {}}})) == ""
    assert _fw_ver_of(json.dumps({"header": {"ts": "123"}, "body": {}})) == ""
    assert _fw_ver_of("not json") == ""
    assert _fw_ver_of(json.dumps(["a", "list"])) == ""


@pytest.mark.usefixtures("clean_database")
async def test_the_firmware_version_of_the_robot_is_saved(helper_bot: MQTTHelperBot) -> None:
    """The version the robot reports is kept in the entry of the bot."""
    bot_repo.add("bot", "did_1234", "p95mgv", "res_123", "eco-ng")
    assert bot_repo.get("did_1234").fw_ver == ""

    payload = json.dumps({"header": {"fwVer": "1.2.3"}, "body": {}})
    helper_bot._remember_fw_ver("did_1234", payload)

    bot = bot_repo.get("did_1234")
    assert bot is not None
    assert bot.fw_ver == "1.2.3"


@pytest.mark.usefixtures("clean_database")
async def test_the_firmware_version_is_written_once_per_version(helper_bot: MQTTHelperBot) -> None:
    """The database is only written when the version of the robot changes."""
    bot_repo.add("bot", "did_1234", "p95mgv", "res_123", "eco-ng")
    payload = json.dumps({"header": {"fwVer": "1.2.3"}, "body": {}})

    helper_bot._remember_fw_ver("did_1234", payload)
    helper_bot._remember_fw_ver("did_1234", payload)

    bot = bot_repo.get("did_1234")
    assert bot is not None
    assert bot.fw_ver == "1.2.3"

    # A new version is written, a message without a version is not read.
    helper_bot._remember_fw_ver("did_1234", json.dumps({"header": {"fwVer": "1.2.4"}, "body": {}}))
    bot = bot_repo.get("did_1234")
    assert bot is not None
    assert bot.fw_ver == "1.2.4"


@pytest.mark.usefixtures("clean_database")
async def test_the_firmware_version_is_not_written_again_after_a_restart(helper_bot: MQTTHelperBot) -> None:
    """The database is not written when it knows the version already."""
    bot_repo.add("bot", "did_1234", "p95mgv", "res_123", "eco-ng")
    bot_repo.set_fw_ver("did_1234", "1.2.3")

    # A helper bot that starts with an empty cache.
    helper_bot._fw_vers.clear()
    payload = json.dumps({"header": {"fwVer": "1.2.3"}, "body": {}})
    helper_bot._remember_fw_ver("did_1234", payload)

    bot = bot_repo.get("did_1234")
    assert bot is not None
    assert bot.fw_ver == "1.2.3"
    # The version is known now, so the next message is not even parsed.
    assert helper_bot._fw_vers["did_1234"] == "1.2.3"


@pytest.mark.usefixtures("clean_database")
async def test_the_firmware_version_is_saved_under_the_did_of_the_command(
    helper_bot: MQTTHelperBot,
) -> None:
    """The robot the command was sent to is the one the version belongs to."""
    bot_repo.add("bot", "did_1234", "p95mgv", "res_123", "eco-ng")

    cmd = MQTTCommandModel(
        {"cmd": "getBattery", "did": "did_1234", "mid": "p95mgv", "res": "res_123", "data": {}},
        version=MQTTCommandModel.VERSION_P2P,
    )
    command = CommandDto(cmd.payload_type, cmd.did or "")
    helper_bot._commands[cmd.request_id] = command

    payload = json.dumps({"header": {"fwVer": "1.2.3"}, "body": {}})
    await helper_bot._on_message(
        Topic(f"iot/p2p/getBattery/helperbot/bumper/helperbot/did_1234/ls1ok3/res_123/p/{cmd.request_id}/j"),
        payload.encode(),
    )

    bot = bot_repo.get("did_1234")
    assert bot is not None
    assert bot.fw_ver == "1.2.3"
    # No other bot was created for the name of the client.
    assert len(bot_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database")
async def test_last_time_stats_stores_a_completed_clean_log(helper_bot: MQTTHelperBot) -> None:
    """The final stats event creates a log with its robot timestamp as the end."""
    did = "did_goat"
    rid = "resource_goat"
    payload = {
        "header": {"ts": "1792845283566600962"},
        "body": {
            "code": 0,
            "msg": "ok",
            "data": {
                "area": 580100,
                "cid": "123",
                "start": "1792840184",
                "stop": 1,
                "time": 2714,
                "type": "auto",
            },
        },
    }

    await helper_bot._on_message(
        Topic(f"iot/atr/onLastTimeStats/{did}/300lc5/{rid}/j"),
        json.dumps(payload).encode(),
    )

    log = clean_log_repo.list_by_id(f"{did}@1792840184@{rid}")
    assert log is not None
    assert log.end == 1792845283
    assert log.last == 2714
    assert log.area == 580100
    assert log.stop_reason is None
