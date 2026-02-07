"""Helper bot module."""

import asyncio
import contextlib
import json
import logging
import random
import ssl
import string
from typing import TYPE_CHECKING, Any

from aiohttp import web
from aiohttp.web_response import Response
from aiomqtt import Client as MQTTClient, MqttError, Topic
from cachetools import TTLCache

from bumper.mqtt.handle_atr import clean_log
from bumper.utils import utils
from bumper.web.utils.response_helper import response_error_v8, response_success_v2

if TYPE_CHECKING:
    from collections.abc import MutableMapping

_LOGGER = logging.getLogger(__name__)
HELPER_BOT_CLIENT_ID = "helperbot@bumper/helperbot"
HELPER_BOT_CLIENT_ID_MQTT = HELPER_BOT_CLIENT_ID.replace("@", "/")
RECONNECT_INTERVAL = 5  # seconds


class MQTTCommandModel:
    """MQTT Command Model."""

    VERSION_OLD = "1"
    VERSION_NEW = "2"
    VERSION_P2P = "p2p"

    request_id: str
    version: str = VERSION_OLD

    payload_type: str
    payload: str
    cmd_name: str | None
    did: str | None
    to_type: str | None
    to_res: str | None
    td: str | None

    def __init__(self, cmdjson: dict[str, Any], version: str = VERSION_OLD) -> None:
        """MQTT Command Model init."""
        self.request_id = "".join(random.sample(string.ascii_letters, 4))
        self.version = version
        if version == self.VERSION_OLD:
            self.from_version_1(cmdjson)
        elif version == self.VERSION_NEW:
            self.from_version_2(cmdjson)
        elif version == self.VERSION_P2P:
            self.from_version_p2p(cmdjson)
        else:
            msg = f"Unsupported version: {version}"
            _LOGGER.error(msg)
            raise ValueError(msg)

    def from_version_1(self, cmdjson: dict[str, Any]) -> None:
        """Parse command information from version 1."""
        self.payload_type = cmdjson.get("payloadType", "j")
        self.cmd_name = cmdjson.get("cmdName")
        self.did = cmdjson.get("toId")
        self.to_type = cmdjson.get("toType")
        self.to_res = cmdjson.get("toRes")
        self.td = cmdjson.get("td")

        payload_j = cmdjson.get("payload")
        self.payload = json.dumps(payload_j) if self.payload_type == "j" else str(payload_j)

    def from_version_2(self, cmdjson: dict[str, Any]) -> None:
        """Parse command information from version 2."""
        self.payload_type = cmdjson.get("fmt", "j")
        self.cmd_name = cmdjson.get("apn")
        self.did = cmdjson.get("eid")
        self.to_type = cmdjson.get("et")
        self.to_res = cmdjson.get("er")
        self.td = cmdjson.get("ct")

        payload_j = cmdjson.get("payload")
        self.payload = json.dumps(payload_j) if self.payload_type == "j" else str(payload_j)

    def from_version_p2p(self, cmdjson: dict[str, Any]) -> None:
        """Parse command information from version p2p."""
        self.payload_type = "j"

        self.cmd_name = cmdjson.get("cmd")
        self.cmd_name_orig = cmdjson.get("cmd")
        self.cmd_name = self.cmd_name[0].lower() + self.cmd_name[1:] if self.cmd_name else None
        if self.cmd_name == "getBatteryInfo":
            self.cmd_name = "getBattery"

        self.did = cmdjson.get("did")
        self.to_type = cmdjson.get("mid")
        self.to_res = cmdjson.get("res")
        # self.td = cmdjson.get("")

        payload_j: dict[str, Any] | None = cmdjson.get("data")
        if payload_j and self.cmd_name == "clean":
            act_translation = {
                "s": "start",
                "p": "pause",
                "r": "resume",
                "t": "stop",
            }
            if act := payload_j.get("act"):
                payload_j["act"] = act_translation.get(act, act)
        if payload_j:
            payload_j = {"body": {"data": payload_j}}

        self.payload = json.dumps(payload_j) if self.payload_type == "j" else str(payload_j)

    def create_topic(self) -> str:
        """Create the MQTT topic for the command."""
        return (
            f"iot/p2p/{self.cmd_name}/{HELPER_BOT_CLIENT_ID_MQTT}/{self.did}/"
            f"{self.to_type}/{self.to_res}/q/{self.request_id}/{self.payload_type}"
        )


class MQTTHelperBot:
    """Helper bot, which converts commands from the rest api to mqtt ones."""

    def __init__(self, host: str, port: int, use_ssl: bool, timeout: float = 60) -> None:
        """MQTT helper bot init."""
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._timeout = timeout
        self._is_connected = False  # Track connection state
        self._client: MQTTClient | None = None  # MQTT client instance
        self._commands: MutableMapping[str, CommandDto] = TTLCache(maxsize=timeout * 60, ttl=timeout * 1.1)
        self._mqtt_task: asyncio.Task[None] | None = None  # Task for managing MQTT connection

    @property
    async def is_connected(self) -> bool:
        """Return True if client is connected successfully."""
        for _ in range(10):  # Retry for up to 1 second
            if self._is_connected:
                break
            await asyncio.sleep(0.1)
        return self._is_connected

    async def start(self) -> None:
        """Start the helper bot and manage the MQTT connection."""
        if self._mqtt_task is None or self._mqtt_task.done():
            self._mqtt_task = asyncio.create_task(self._mqtt_loop())

    async def disconnect(self) -> None:
        """Disconnect helper bot."""
        _LOGGER.info("Disconnecting HelperBot...")
        if self._mqtt_task:
            self._mqtt_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._mqtt_task
            self._mqtt_task = None
        # Explicitly set the client to None to ensure cleanup
        self._client = None
        self._is_connected = False

    async def _mqtt_loop(self) -> None:
        """Manage MQTT connection and reconnection in the main loop."""
        while True:
            try:
                ssl_ctx: ssl.SSLContext | None = None
                if self._use_ssl:
                    ssl_ctx = ssl.create_default_context()
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE

                async with MQTTClient(
                    hostname=self._host,
                    port=self._port,
                    tls_context=ssl_ctx,
                    identifier=HELPER_BOT_CLIENT_ID,
                ) as client:
                    self._client = client
                    self._is_connected = True
                    _LOGGER.info("Helper Bot connected successfully.")
                    await self._subscribe_topics()

                    # Listen for messages
                    async for message in client.messages:
                        await self._on_message(message.topic, message.payload)
            except MqttError as e:
                self._is_connected = False
                _LOGGER.warning(f"MQTT connection lost: {e}. Reconnecting in {RECONNECT_INTERVAL} seconds...")
                await asyncio.sleep(RECONNECT_INTERVAL)
            except Exception:
                self._is_connected = False
                _LOGGER.exception("Unexpected error in MQTT loop")
                await asyncio.sleep(RECONNECT_INTERVAL)

    async def send_command(self, cmd: MQTTCommandModel) -> Response:
        """Send command over MQTT."""
        try:
            if not await self.is_connected:
                await self.start()

            topic = cmd.create_topic()
            command_dto = CommandDto(cmd.payload_type)
            self._commands[cmd.request_id] = command_dto

            _LOGGER.debug(f"Sending message :: topic={topic} :: payload={cmd.payload}")
            await self.publish(topic, cmd.payload)

            cmd_response = await self._wait_for_resp(command_dto)
            _LOGGER.debug(f"To   Bot  Request :: {cmd.__dict__}")
            _LOGGER.debug(f"From Bot Response :: {cmd_response}")

            # try:
            #     if cmd_response.get("header", {}).get("fwVer"):
            #         cmd_response["header"]["fwVer"] = "1.7.5"
            #     if cmd_response.get("header", {}).get("tzm"):
            #         cmd_response["header"]["tzm"] = 120
            #     if cmd_response.get("body", {}).get("data", {}).get("ver"):
            #         cmd_response["body"]["data"]["ver"] = "1.7.5"
            # except Exception:
            #     pass

            if cmd_response is None:
                return response_error_v8(cmd.request_id, "wait for response timed out")

            # Calls by '/iot/devmanager.do'
            if cmd.version == cmd.VERSION_OLD:
                return web.json_response(
                    {
                        "id": cmd.request_id,
                        "ret": "ok",
                        "resp": cmd_response,
                        "payloadType": cmd.payload_type,
                    },
                )

            # Calls by 'iot/endpoint/control'
            if cmd.version == cmd.VERSION_NEW:
                return web.Response(
                    body=json.dumps(cmd_response, separators=(",", ":")).encode("utf-8"),
                    content_type="application/octet-stream",
                    charset="utf-8",
                    headers={
                        "x-ngiot-fmt": "b",
                        "x-ngiot-ret": "ok",
                    },
                )

            # Calls by 'appsvr/app.do' with 'RobotControl'
            if cmd.version == cmd.VERSION_P2P and isinstance(cmd_response, dict):
                ret_type: dict[str, Any] | None = None
                if cmd.cmd_name == "getBattery":
                    ret_type = {"key": "power", "value": cmd_response.get("body", {}).get("data", {}).get("value")}
                elif cmd.cmd_name == "getChargeState":
                    is_charging: int = cmd_response.get("body", {}).get("data", {}).get("isCharging")
                    mode = "SlotCharging" if is_charging == 1 else "SlotIdle"
                    ret_type = {"key": "type", "value": mode}
                elif cmd.cmd_name in {"charge", "clean"}:
                    return response_success_v2(
                        data={cmd.cmd_name_orig: {"did": cmd.did, "ret": cmd_response.get("body", {}).get("msg", "error")}},
                    )
                if ret_type is not None:
                    return response_success_v2(
                        data={cmd.cmd_name_orig: {"ret": "ok", "did": cmd.did, ret_type["key"]: ret_type["value"]}},
                    )
                return response_success_v2(data={cmd.cmd_name_orig: {"ret": "ok", "did": cmd.did}})

            msg = f"Unsupported version :: '{cmd.version}' :: {cmd_response}"
            _LOGGER.error(msg)
            return response_error_v8(cmd.request_id, msg)
        except Exception:
            _LOGGER.exception("Could not send command")
            return response_error_v8(cmd.request_id, "exception occurred please check bumper logs")
        finally:
            self._commands.pop(cmd.request_id, None)

    async def publish(self, topic: str, payload: str) -> None:
        """Publish message."""
        if not self._client:
            error_message = "MQTT client is not connected."
            raise MqttError(error_message)
        await self._client.publish(topic, payload.encode())

    async def _wait_for_resp(self, command_dto: "CommandDto") -> str | dict[str, Any] | None:
        """Wait for response."""
        try:
            return await asyncio.wait_for(command_dto.wait_for_response(), timeout=self._timeout)
        except TimeoutError:
            _LOGGER.debug("wait_for_resp timeout reached")
        except asyncio.CancelledError:
            _LOGGER.debug("wait_for_resp cancelled by asyncio", exc_info=True)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during wait for response"))
        return None

    async def _subscribe_topics(self) -> None:
        """Subscribe to required topics."""
        if not self._client:
            error_message = "MQTT client is not connected."
            raise MqttError(error_message)
        await self._client.subscribe(f"iot/p2p/+/+/+/+/{HELPER_BOT_CLIENT_ID_MQTT}/+/+/+")
        await self._client.subscribe("iot/atr/+/+/+/+/+")

    async def _on_message(self, topic: Topic, payload: Any) -> None:
        """Handle incoming messages."""
        try:
            decoded_payload: str = payload.decode("utf-8", errors="replace")

            _LOGGER.debug(f"Got message :: topic={topic.value} :: payload={decoded_payload}")
            topic_split = topic.value.split("/")  # Use `topic.value` to get the string representation
            if topic_split[1] == "p2p" and topic_split[10] in self._commands:
                self._commands[topic_split[10]].add_response(decoded_payload)
            elif topic_split[1] == "atr" and topic_split[2] in ("onStats", "reportStats"):
                clean_log(did=topic_split[3], rid=topic_split[5], payload=decoded_payload)
            elif topic_split[1] == "atr":
                # pass  # NOTE: check later to use for some server side information to display
                _LOGGER.debug(
                    {
                        "info": "ATR :: Provided message is not implemented to be processed",
                        "type": topic_split[1],
                        "function": topic_split[2],
                        "did": topic_split[3],
                        "class": topic_split[4],
                        "rid": topic_split[5],
                        "payloadType": topic_split[6],
                        "payload": decoded_payload,
                    },
                )
            elif topic_split[1] == "p2p":
                _LOGGER.debug(
                    {
                        "info": "P2P :: Provided message is not implemented to be processed",
                        "type": topic_split[1],
                        "function": topic_split[2],
                        "did": topic_split[3],
                        "class": topic_split[4],
                        "rid": topic_split[5],
                        "payloadType": topic_split[6],
                        "payload": decoded_payload,
                    },
                )
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="on message"))
            raise


class CommandDto:
    """Command DTO."""

    def __init__(self, payload_type: str) -> None:
        """Command DTO init."""
        self._payload_type = payload_type
        self._event = asyncio.Event()
        self._response: str | bytes | None = None

    async def wait_for_response(self) -> str | dict[str, Any] | None:
        """Wait for the response to be received."""
        await self._event.wait()
        if self._payload_type == "j" and self._response is not None:
            res = json.loads(self._response)
            if isinstance(res, dict):
                return res
        return str(self._response) if self._response is not None else None

    def add_response(self, response: str | bytes) -> None:
        """Add received response."""
        self._response = response
        self._event.set()
