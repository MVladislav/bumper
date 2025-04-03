"""Mqtt proxy module."""

import asyncio
import contextlib
import logging
import ssl
import typing
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

from amqtt.adapters import StreamReaderAdapter, StreamWriterAdapter, WebSocketsReader, WebSocketsWriter
from amqtt.client import MQTTClient, Session
from amqtt.errors import ConnectError, ProtocolHandlerError
from amqtt.mqtt.connack import CONNECTION_ACCEPTED, SERVER_UNAVAILABLE
from amqtt.mqtt.constants import QOS_0
from amqtt.mqtt.protocol.client_handler import ClientProtocolHandler
from cachetools import TTLCache
import websockets
from websockets.exceptions import InvalidHandshake, InvalidURI

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
        config: dict[str, Any] | None = None,
        timeout: float = 180,
    ) -> None:
        """Mqtt proxy client init."""
        self.request_mapper: MutableMapping[str, str] = TTLCache(maxsize=timeout * timeout, ttl=timeout * 1.1)
        self._client: MQTTClient = _NoCertVerifyClient(client_id=client_id, config=config)
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


class _NoCertVerifyClient(MQTTClient):  # type:ignore[misc]
    # pylint: disable=all
    """Mqtt client, which is not verify the certificate.

    Purpose is only to add "sc.verify_mode = ssl.CERT_NONE  # Ignore verify of cert"
    """

    @typing.no_type_check
    async def _connect_coro(self) -> Literal[0, 1, 2, 3, 4, 5]:
        if self.session is None:
            return SERVER_UNAVAILABLE
        if isinstance(self.session, Session) is False:
            return SERVER_UNAVAILABLE

        kwargs = {}

        # Decode URI attributes
        uri_attributes = urlparse(self.session.broker_uri)
        scheme = uri_attributes.scheme
        secure = scheme in ("mqtts", "wss")
        self.session.username = self.session.username if self.session.username else uri_attributes.username
        self.session.password = self.session.password if self.session.password else uri_attributes.password
        self.session.remote_address = uri_attributes.hostname
        self.session.remote_port = uri_attributes.port
        if scheme in ("mqtt", "mqtts") and not self.session.remote_port:
            self.session.remote_port = 8883 if scheme == "mqtts" else 1883
        if scheme in ("ws", "wss") and not self.session.remote_port:
            self.session.remote_port = 443 if scheme == "wss" else 80
        if scheme in ("ws", "wss"):
            # Rewrite URI to conform to https://tools.ietf.org/html/rfc6455#section-3
            uri = [
                scheme,
                f"{self.session.remote_address}:{self.session.remote_port!s}",
                uri_attributes[2],
                uri_attributes[3],
                uri_attributes[4],
                uri_attributes[5],
            ]
            self.session.broker_uri = urlunparse(uri)
        # Init protocol handler
        # if not self._handler:
        self._handler = ClientProtocolHandler(self.plugins_manager)

        if secure:
            sc = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.session.cafile,
                capath=self.session.capath,
                cadata=self.session.cadata,
            )
            if "certfile" in self.config and "keyfile" in self.config:
                sc.load_cert_chain(self.config["certfile"], self.config["keyfile"])
            if "check_hostname" in self.config and isinstance(self.config["check_hostname"], bool):
                sc.check_hostname = self.config["check_hostname"]

            sc.verify_mode = ssl.CERT_NONE  # Ignore verify of cert
            kwargs["ssl"] = sc

        try:
            reader = None
            writer = None
            self._connected_state.clear()
            # Open connection
            if scheme in ("mqtt", "mqtts"):
                conn_reader, conn_writer = await asyncio.open_connection(
                    self.session.remote_address,
                    self.session.remote_port,
                    **kwargs,
                )
                reader = StreamReaderAdapter(conn_reader)
                writer = StreamWriterAdapter(conn_writer)
            elif scheme in ("ws", "wss"):
                websocket = await websockets.connect(
                    self.session.broker_uri,
                    subprotocols=["mqtt"],
                    extra_headers=self.extra_headers,
                    **kwargs,
                )
                reader = WebSocketsReader(websocket)
                writer = WebSocketsWriter(websocket)
            # Start MQTT protocol
            self._handler.attach(self.session, reader, writer)
            return_code = await self._handler.mqtt_connect()

            if return_code is not CONNECTION_ACCEPTED:
                self.session.transitions.disconnect()
                self.logger.warning(f"Connection rejected with code '{return_code}'")
                exc = ConnectError("Connection rejected by broker")
                exc.return_code = return_code
                raise exc

            # Handle MQTT protocol
            await self._handler.start()
            self.session.transitions.connect()
            self._connected_state.set()
            self.logger.debug(f"connected to {self.session.remote_address}:{self.session.remote_port}")

            return return_code
        except InvalidURI:
            self.logger.warning(f"connection failed: invalid URI '{self.session.broker_uri}'")
            self.session.transitions.disconnect()
            # raise ConnectError(f"connection failed: invalid URI '{self.session.broker_uri}'", iuri)
            raise
        except InvalidHandshake:
            self.logger.warning("connection failed: invalid websocket handshake")
            self.session.transitions.disconnect()
            # raise ConnectError("connection failed: invalid websocket handshake", ihs)
            raise
        except (ProtocolHandlerError, ConnectionError, OSError) as e:
            self.logger.warning(f"MQTT connection failed: {e}")
            self.session.transitions.disconnect()
            # raise ConnectError(e)
            raise
