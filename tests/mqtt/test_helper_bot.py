import asyncio
import json
import time

from aiomqtt import Client
import pytest
from testfixtures import LogCapture

from bumper.mqtt.helper_bot import MQTTCommandModel, MQTTHelperBot
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
    assert cmd.cmd_name == "clean"  # clean_V2 -> clean
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
async def test_helperbot_connect() -> None:
    mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
    try:
        await mqtt_helperbot.start()
        assert await mqtt_helperbot.is_connected
    finally:
        await mqtt_helperbot.disconnect()
        assert not await mqtt_helperbot.is_connected
        assert mqtt_helperbot._client is None
        assert mqtt_helperbot._mqtt_task is None


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
            msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/wC3g/x"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Broadcast :: Topic: iot/atr/DustCaseST/bot_serial/ls1ok3/wC3g/x"
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
            msg_topic_name = "iot/p2p/GetWKVer/helperbot/bumper/helperbot/bot_serial/ls1ok3/wC3g/q/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Send Command :: Topic: iot/p2p/GetWKVer/helperbot/bumper/helperbot/bot_serial/ls1ok3/wC3g/q/iCmuqp/j"
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
            msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Response"
                        " :: Topic: iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/iCmuqp/j"
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
            msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/TESTBAD/bumper/helperbot/p/iCmuqp/j"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.2)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Message :: Topic: iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/TESTBAD/bumper/helperbot/p/iCmuqp/j"
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
            msg_topic_name = "iot/atr/errors/bot_serial/ls1ok3/wC3g/x"
            await mqtt_client.publish(msg_topic_name, msg_payload.encode())

            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "bumper.mqtt.server.messages",
                    "DEBUG",
                    (
                        "Received Broadcast :: Topic: iot/atr/errors/bot_serial/ls1ok3/wC3g/x"
                        " :: Message: <ctl ts='1560904925396' td='errors' old='' new='110'/>"
                    ),
                ),
            )  # Check received message was logged
            log.clear()
        finally:
            await mqtt_helperbot.disconnect()


async def test_helperbot_expire_message(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    expire_msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    expire_msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/testgood/j"
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
    msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/wC3g/x"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())  # Send another message to force get_msg

    await asyncio.sleep(0.1 * 2)

    assert helper_bot._commands.get(request_id, None) is None


async def test_helperbot_send_command(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    cmdjson = {
        "toType": "ls1ok3",
        "payloadType": "j",
        "toRes": "wC3g",
        "payload": {},
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "GetWKVer",
        "auth": {
            "token": "us_52cb21fef8e547f38f4ec9a699a5d77e",
            "resource": "IOSF53D07BA",
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
    msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/testgood/j"
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
        "toRes": "wC3g",
        "payload": '<ctl type="Brush"/>',
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "GetLifeSpan",
        "auth": {
            "token": "us_52cb21fef8e547f38f4ec9a699a5d77e",
            "resource": "IOSF53D07BA",
            "userid": "testuser",
            "with": "users",
            "realm": "ecouser.net",
        },
    }

    # Send response beforehand
    msg_payload = "<ctl ret='ok' type='Brush' left='4142' total='18000'/>"
    msg_topic_name = "iot/p2p/GetLifeSpan/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/testx/q"
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
        "toRes": "wC3g",
        "payload": {"header": {"pri": 1, "ts": "1569380075887", "tzm": -240, "ver": "0.0.50"}},
        "td": "q",
        "toId": "bot_serial",
        "cmdName": "getStats",
        "auth": {
            "token": "us_52cb21fef8e547f38f4ec9a699a5d77e",
            "resource": "IOSF53D07BA",
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

    msg_topic_name = "iot/p2p/getStats/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/testj/j"
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
    # Do not send a response, so it times out
    result = await helper_bot.send_command_plain(cmd)
    assert result is None


async def test_helperbot_send_command_plain_valid_response(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
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

    # Give the command time to be published and the CommandDto to be registered

    # Publish the response to a topic where the request_id is at index 10
    msg_payload = '{"body": {"data": {"value": 80}}}'
    msg_topic_name = f"iot/p2p/getBattery/did_valid/ls1ok3/res_valid/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    # Wait for the response
    result = await send_task
    assert result == {"body": {"data": {"value": 80}}}


async def test_helperbot_send_command_old(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
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

    msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    msg_topic_name = f"iot/p2p/GetWKVer/did_old/ls1ok3/res_old/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["resp"] == {"ret": "ok", "ver": "0.13.5"}


async def test_helperbot_send_command_new(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
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
    cmdjson = {
        "cmd": "getBatteryInfo",
        "did": "did_battery",
        "mid": "ls1ok3",
        "res": "res_battery",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))

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
    cmdjson = {
        "cmd": "getChargeState",
        "did": "did_charge",
        "mid": "ls1ok3",
        "res": "res_charge",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))

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


async def test_helperbot_send_command_p2p_charge(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
    cmdjson = {
        "cmd": "charge",
        "did": "did_charge_cmd",
        "mid": "ls1ok3",
        "res": "res_charge_cmd",
        "data": {},
    }
    cmd = MQTTCommandModel(cmdjson, version=MQTTCommandModel.VERSION_P2P)

    send_task = asyncio.create_task(helper_bot._send_command_p2p(cmd))

    msg_payload = '{"body": {"msg": "ok"}}'
    msg_topic_name = f"iot/p2p/charge/did_charge_cmd/ls1ok3/res_charge_cmd/helperbot/bumper/helperbot/p/{cmd.request_id}/j"
    await mqtt_client.publish(msg_topic_name, msg_payload.encode())

    result = await send_task
    assert result.status == 200
    json_resp = json.loads(result.text)
    assert json_resp["ret"] == "ok"
    assert json_resp["data"]["charge"]["ret"] == "ok"
    assert json_resp["data"]["charge"]["did"] == "did_charge_cmd"
