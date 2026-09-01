"""Mqtt proxy module."""

import asyncio
import contextlib
import logging
import typing
from typing import Any

from amqtt.client import ClientConfig, MQTTClient
from amqtt.mqtt.constants import QOS_0
from cachetools import TTLCache

from bumper.utils.settings import config as bumper_isc

if typing.TYPE_CHECKING:
    from collections.abc import MutableMapping

_LOGGER = logging.getLogger(__name__)

# iot/p2p/[command]]/[sender did]/[sender class]]/[sender resource]
# /[receiver did]/[receiver class]]/[receiver resource]/[q|p/[request id/j
# [q|p] q-> request p-> response


class ProxyClient:
    """Mqtt client, which proxies all messages to the ecovacs servers."""

    def __init__(
        self,
        client_id: str,
        host: str,
        port: int = bumper_isc.WEB_SERVER_TLS_LISTEN_PORT,
        config: ClientConfig | dict[str, Any] | None = None,
        timeout: float = 180,
    ) -> None:
        """Mqtt proxy client init."""
        self.request_mapper: MutableMapping[str, str] = TTLCache(maxsize=timeout * timeout, ttl=timeout * 1.1)
        if config is None:
            config = ClientConfig(check_hostname=False, verify_cert=False)
        self._client = MQTTClient(client_id=client_id, config=config)
        self._host = host
        self._port = port

    async def connect(self, username: str, password: str) -> None:
        """Connect."""
        try:
            await self._client.connect(f"mqtts://{username}:{password}@{self._host}:{self._port}")
        except Exception:
            _LOGGER.exception("An exception occurred during startup")
            raise

        asyncio.Task(self._handle_messages())

    async def _handle_messages(self) -> None:
        if self._client.session is None or bumper_isc.mqtt_helperbot is None:
            return

        while self._client.session.transitions.is_connected():
            try:
                message = await self._client.deliver_message()
                if message is None:
                    return

                data = ""
                if message.data is not None:
                    data = message.data.decode("utf-8")

                _LOGGER.info(f"Message Received From Ecovacs - Topic: {message.topic} - Message: {data}")
                topic = message.topic
                ttopic = topic.split("/")
                if ttopic[1] == "p2p":
                    if ttopic[3] == "proxyhelper":
                        _LOGGER.error(f'"proxyhelper" was sender - INVALID!! Topic: {topic}')
                        continue

                    self.request_mapper[ttopic[10]] = ttopic[3]
                    ttopic[3] = "proxyhelper"
                    topic = "/".join(ttopic)
                    _LOGGER.info(f"Converted Topic From {message.topic} TO {topic}")

                _LOGGER.info(f"Proxy Forward Message to Robot - Topic: {topic} - Message: {data}")

                await bumper_isc.mqtt_helperbot.publish(topic, data)
            except Exception:
                _LOGGER.exception("An error occurred during handling a message")

    async def subscribe(self, topic: str, qos: Any = QOS_0) -> None:
        """Subscribe to topic."""
        await self._client.subscribe([(topic, qos)])

    async def disconnect(self) -> None:
        """Disconnect."""
        with contextlib.suppress(AttributeError):
            await self._client.disconnect()

    async def publish(self, topic: str, message: bytes, qos: int | None = None) -> None:
        """Publish message."""
        await self._client.publish(topic, message, qos)
