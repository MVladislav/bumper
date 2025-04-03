"""Helper bot module."""

import asyncio
import contextlib
import json
import logging
import ssl
from typing import TYPE_CHECKING, Any

from aiomqtt import Client as MQTTClient, MqttError, Topic
from cachetools import TTLCache

from bumper.mqtt.handle_atr import clean_log
from bumper.utils import utils

if TYPE_CHECKING:
    from collections.abc import MutableMapping

_LOGGER = logging.getLogger(__name__)
HELPER_BOT_CLIENT_ID = "helperbot@bumper/helperbot"
RECONNECT_INTERVAL = 5  # seconds


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

    async def send_command(self, cmdjson: dict[str, Any], request_id: str) -> dict[str, Any]:
        """Send command over MQTT."""
        try:
            if not await self.is_connected:
                await self.start()

            payload_type = cmdjson.get("payloadType", "x")
            payload = cmdjson.get("payload")

            topic = (
                f"iot/p2p/{cmdjson['cmdName']}/helperbot/bumper/helperbot/{cmdjson['toId']}/"
                f"{cmdjson['toType']}/{cmdjson['toRes']}/q/{request_id}/{payload_type}"
            )

            payload = json.dumps(payload) if payload_type == "j" else str(payload)

            command_dto = CommandDto(payload_type)
            self._commands[request_id] = command_dto

            _LOGGER.debug(f"Sending message :: topic={topic} :: payload={payload}")
            await self.publish(topic, payload)

            return await self._wait_for_resp(command_dto, request_id)
        except Exception:
            _LOGGER.exception("Could not send command")
            return {
                "id": request_id,
                "errno": 500,
                "ret": "fail",
                "debug": "exception occurred please check bumper logs",
            }
        finally:
            self._commands.pop(request_id, None)

    async def publish(self, topic: str, payload: str) -> None:
        """Publish message."""
        if not self._client:
            error_message = "MQTT client is not connected."
            raise MqttError(error_message)
        await self._client.publish(topic, payload.encode())

    async def _wait_for_resp(self, command_dto: "CommandDto", request_id: str) -> dict[str, Any]:
        """Wait for response."""
        try:
            return {
                "id": request_id,
                "ret": "ok",
                "resp": await asyncio.wait_for(command_dto.wait_for_response(), timeout=self._timeout),
            }
        except TimeoutError:
            _LOGGER.debug("wait_for_resp timeout reached")
        except asyncio.CancelledError:
            _LOGGER.debug("wait_for_resp cancelled by asyncio", exc_info=True)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during wait for response"))
        return {
            "id": request_id,
            "errno": 500,
            "ret": "fail",
            "debug": "wait for response timed out",
        }

    async def _subscribe_topics(self) -> None:
        """Subscribe to required topics."""
        if not self._client:
            error_message = "MQTT client is not connected."
            raise MqttError(error_message)
        await self._client.subscribe("iot/p2p/+/+/+/+/helperbot/bumper/helperbot/+/+/+")
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
                pass  # NOTE: check later to use for some server side information to display
            elif topic_split[1] == "p2p":
                _LOGGER.warning(
                    {
                        "info": "Provided message is not implemented to be processed",
                        "type": topic_split[1],
                        "function": topic_split[2],
                        "did": topic_split[3],
                        "class": topic_split[4],
                        "rid": topic_split[5],
                        "other2": topic_split[6],
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
