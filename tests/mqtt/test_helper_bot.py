import asyncio
import time

from gmqtt import Client
from testfixtures import LogCapture

from bumper.mqtt.helper_bot import MQTTHelperBot
from tests import HOST, MQTT_PORT


async def test_helperbot_connect(mqtt_client: Client) -> None:
    # Test helperbot connect
    mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
    await mqtt_helperbot.start()
    assert mqtt_helperbot.is_connected
    await mqtt_helperbot.disconnect()


async def test_helperbot_message(mqtt_client: Client) -> None:
    with LogCapture() as log:
        # Test broadcast message
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        await mqtt_helperbot.start()
        assert mqtt_helperbot.is_connected
        msg_payload = "<ctl ts='1547822804960' td='DustCaseST' st='0'/>"
        msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/wC3g/x"
        mqtt_client.publish(msg_topic_name, msg_payload.encode())

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
        await mqtt_helperbot.disconnect()

        # Send command to bot
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        await mqtt_helperbot.start()
        assert mqtt_helperbot.is_connected
        msg_payload = "{}"
        msg_topic_name = "iot/p2p/GetWKVer/helperbot/bumper/helperbot/bot_serial/ls1ok3/wC3g/q/iCmuqp/j"
        mqtt_client.publish(msg_topic_name, msg_payload.encode())

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
        await mqtt_helperbot.disconnect()

        # Received response to command
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        await mqtt_helperbot.start()
        assert mqtt_helperbot.is_connected
        msg_payload = '{"ret":"ok","ver":"0.13.5"}'
        msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/iCmuqp/j"
        mqtt_client.publish(msg_topic_name, msg_payload.encode())

        await asyncio.sleep(0.1)

        log.check_present(
            (
                "bumper.mqtt.server.messages",
                "DEBUG",
                (
                    "Received Response :: Topic: iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/iCmuqp/j"
                    ' :: Message: {"ret":"ok","ver":"0.13.5"}'
                ),
            ),
        )  # Check received response message was logged
        log.clear()
        await mqtt_helperbot.disconnect()

        # Received unknown message
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        await mqtt_helperbot.start()
        assert mqtt_helperbot.is_connected
        msg_payload = "test"
        msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/TESTBAD/bumper/helperbot/p/iCmuqp/j"
        mqtt_client.publish(msg_topic_name, msg_payload.encode())

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
        await mqtt_helperbot.disconnect()

        # Received error message
        mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True)
        await mqtt_helperbot.start()
        assert mqtt_helperbot.is_connected
        msg_payload = "<ctl ts='1560904925396' td='errors' old='' new='110'/>"
        msg_topic_name = "iot/atr/errors/bot_serial/ls1ok3/wC3g/x"
        mqtt_client.publish(msg_topic_name, msg_payload.encode())

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

    helper_bot._commands[request_id] = data  # type: ignore

    assert helper_bot._commands[request_id] == data

    await asyncio.sleep(0.1)
    msg_payload = "<ctl ts='1547822804960' td='DustCaseST' st='0'/>"
    msg_topic_name = "iot/atr/DustCaseST/bot_serial/ls1ok3/wC3g/x"
    mqtt_client.publish(msg_topic_name, msg_payload.encode())  # Send another message to force get_msg

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
    commandresult = await helper_bot.send_command(cmdjson, "testfail")
    # Don't send a response, ensure timeout
    assert commandresult == {
        "debug": "wait for response timed out",
        "errno": 500,
        "id": "testfail",
        "ret": "fail",
    }  # Check timeout

    # Send response beforehand
    msg_payload = '{"ret":"ok","ver":"0.13.5"}'
    msg_topic_name = "iot/p2p/GetWKVer/bot_serial/ls1ok3/wC3g/helperbot/bumper/helperbot/p/testgood/j"
    loop = asyncio.get_event_loop()
    loop.call_soon(lambda: mqtt_client.publish(msg_topic_name, msg_payload.encode()))

    commandresult = await helper_bot.send_command(cmdjson, "testgood")
    assert commandresult == {
        "id": "testgood",
        "resp": {"ret": "ok", "ver": "0.13.5"},
        "ret": "ok",
    }

    # await mqtt_helperbot.Client.disconnect()

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
    mqtt_client.publish(msg_topic_name, msg_payload.encode())

    commandresult = await helper_bot.send_command(cmdjson, "testx")
    assert commandresult == {
        "id": "testx",
        "resp": "<ctl ret='ok' type='Brush' left='4142' total='18000'/>",
        "ret": "ok",
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
    mqtt_client.publish(msg_topic_name, msg_payload.encode())

    commandresult = await helper_bot.send_command(cmdjson, "testj")

    assert commandresult == {
        "id": "testj",
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
