import asyncio
import json
import time

from aiomqtt import Client
import pytest
from testfixtures import LogCapture

from bumper.mqtt.helper_bot import MQTTCommandModel, MQTTHelperBot
from tests import HOST, MQTT_PORT


@pytest.mark.usefixtures("mqtt_client")
async def test_helperbot_connect() -> None:
    mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
    try:
        await mqtt_helperbot.start()
        assert await mqtt_helperbot.is_connected
    finally:
        await mqtt_helperbot.disconnect()


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


async def test_helperbot_sendcommand(mqtt_client: Client, helper_bot: MQTTHelperBot) -> None:
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
        "debug": "wait for response timed out",
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
