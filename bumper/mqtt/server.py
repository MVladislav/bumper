"""MQTT Server module."""

import asyncio
import base64
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
import logging
from pathlib import Path
from typing import Literal

from amqtt.broker import Broker
from amqtt.client import ClientConfig
from amqtt.contexts import BaseContext, BrokerConfig, ListenerConfig, ListenerType
from amqtt.plugins.base import BaseAuthPlugin
from amqtt.session import IncomingApplicationMessage, Session
from passlib.apps import custom_app_context as pwd_context

from bumper.db import bot_repo, client_repo, token_repo
from bumper.mqtt import helper_bot, proxy as mqtt_proxy
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)
_LOGGER_MESSAGES = logging.getLogger(f"{__name__}.messages")
_LOGGER_PROXY = logging.getLogger(f"{__name__}.proxy")
_LOGGER_BROKER = logging.getLogger(f"{__name__}.broker")


def _log__helperbot_message(custom_log_message: str, topic: str, data: str) -> None:
    """Log Helper bot messages."""
    _LOGGER_MESSAGES.debug(f"{custom_log_message} :: Topic: {topic} :: Message: {data}")


@dataclasses.dataclass(frozen=True)
class MQTTBinding:
    """Webserver binding."""

    host: str
    port: int
    use_ssl: bool


class MQTTServer:
    """MQTT server."""

    _state_cond = asyncio.Condition()

    def __init__(
        self,
        bindings: list[MQTTBinding] | MQTTBinding,
        password_file: str | None = None,
        allow_anonymous: bool = False,
    ) -> None:
        """MQTT server init."""
        try:
            if isinstance(bindings, MQTTBinding):
                bindings = [bindings]
            self._bindings = bindings

            # For file auth, set user:hash in passwd file see
            # (https://hbmqtt.readthedocs.io/en/latest/references/hbmqtt.html#configuration-example)
            if password_file is None:
                password_file = str(Path(bumper_isc.data_dir) / "passwd")

            config_bind: dict[str, ListenerConfig] = {
                "default": ListenerConfig(type=ListenerType.TCP, bind=None),
            }
            listener_prefix = "mqtt"
            for index, binding in enumerate(self._bindings):
                # If port is 1883 use default as listener name, else create new one
                listener_name = f"{listener_prefix}{index}" if binding.port != 1883 else "default"

                config_bind[listener_name] = ListenerConfig(
                    type=ListenerType.TCP,
                    bind=f"{binding.host}:{binding.port}",
                    ssl=binding.use_ssl,
                )
                if binding.use_ssl is True:
                    config_bind[listener_name].cafile = str(bumper_isc.ca_cert)
                    config_bind[listener_name].certfile = str(bumper_isc.server_cert)
                    config_bind[listener_name].keyfile = str(bumper_isc.server_key)

            # Initialize bot server
            config: BrokerConfig = BrokerConfig(
                listeners=config_bind,
                plugins={
                    "bumper.mqtt.server.BumperMQTTServerPlugin": {
                        "allow_anonymous": allow_anonymous,
                        "password_file": password_file,
                    },
                },
            )

            self._broker = Broker(config=config)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during initialize"))
            raise

    @property
    def state(self) -> str:
        """Return the state of the broker."""
        return str(self._broker.transitions.state)

    @property
    def sessions(self) -> list[Session]:
        """Get sessions."""
        return [session for (session, _) in self._broker.sessions.values()]

    async def start(self) -> None:
        """Start MQTT server."""
        try:
            if self.state not in ["stopping", "starting", "started"]:
                for binding in self._bindings:
                    _LOGGER.info(f"Starting MQTT Server at {binding.host}:{binding.port}")
                await self._broker.start()
            elif self.state == "stopping":
                _LOGGER.warning("MQTT Server is stopping. Waiting for it to stop before restarting...")
                await self.wait_for_state_change("stopping", reverse=True)
                if self.state == "stopped":
                    await self._broker.start()
            else:
                _LOGGER.info("MQTT Server is already running. Stop it first for a clean restart!")
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during startup"))
            raise

    async def shutdown(self) -> None:
        """Shutdown the MQTT server."""
        try:
            if self.state == "started":
                _LOGGER.info("Shutting down MQTT server...")
                await self._broker.shutdown()
                _LOGGER_BROKER.info("Broker closed")
            elif self.state in ["starting"]:
                _LOGGER.warning(f"MQTT server is in '{self.state}' state. Waiting for it to stabilize...")
                await self.wait_for_state_change("starting", reverse=True)
                if self.state == "started":
                    await self._broker.shutdown()
            elif self.state in ["stopping"]:
                _LOGGER.warning(f"MQTT server is in '{self.state}' state. Waiting for it to stabilize...")
                await self.wait_for_state_change("stopping", reverse=True)
            else:
                _LOGGER.warning(f"MQTT server is not in a valid state for shutdown. Current state: {self.state}")
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during shutdown"))
            raise

    async def wait_for_state_change(
        self,
        desired: str,
        max_wait: float = 3.0,
        reverse: bool = False,
    ) -> None:
        """Wait until `state == desired` (reverse=False) or `state != desired` (reverse=True), raising TimeoutError."""
        try:

            def _check() -> bool:
                st = self.state
                _LOGGER.debug(f"Waiting for state :: '{st}' {'!=' if reverse else '=='} '{desired}' …")
                return (reverse and st != desired) or (not reverse and st == desired)

            # Fast path
            if _check():
                return

            async with self._state_cond:
                await asyncio.wait_for(self._state_cond.wait_for(_check), max_wait)
            _LOGGER.debug(f"Reached state :: '{self.state}' {'!=' if reverse else '=='} '{desired}'")
        except TimeoutError:
            _LOGGER.warning(f"Timeout waiting for MQTT server to reach state '{desired}' :: Current state: '{self.state}'")


class BumperMQTTServerPlugin(BaseAuthPlugin):  # type: ignore[misc]
    """MQTT Server plugin which handles the authentication."""

    @dataclass
    class Config:
        """Allow empty username and password file."""

        allow_anonymous: bool = field(default=True)
        password_file: str | None = None

    def __init__(self, context: BaseContext) -> None:
        """MQTT Server plugin init."""
        super().__init__(context)

        self._proxy_clients: dict[str, mqtt_proxy.ProxyClient] = {}
        self._users: dict[str, str] = {}
        self._read_password_file()

    async def authenticate(self, *, session: Session) -> bool | None:
        """Authenticate session."""
        username: str | None = session.username
        password: str | None = session.password  # Format: JWT
        client_id: str | None = session.client_id  # Format: <DID/USER_ID>@<CLASSID>/RESOURCE

        error_msg = "File Authentication Failed :: Default access not grant - last try anonymous auth if allowed!"

        try:
            if client_id is None:
                _LOGGER.warning("Bumper Authentication Failed :: No client_id provided")
                raise Exception(error_msg)

            # Authenticate the HelperBot
            if client_id == helper_bot.HELPER_BOT_CLIENT_ID:
                _LOGGER.info(f"Bumper Authentication Success :: Helperbot :: ClientID: {client_id}")
                return True

            username = username.split("@")[0] if username and "@" in username else username
            session.username = username

            # Check for File Auth
            if "@" not in client_id and username is not None and password is not None:
                password_hash = self._users.get(username)
                message_suffix = f"Username: {username} - ClientID: {client_id}"
                if password_hash is None:
                    _LOGGER.info(f"File Authentication Failed :: No Entry for :: {message_suffix}")
                    raise Exception(error_msg)
                if pwd_context.verify(password, password_hash):
                    _LOGGER.info(f"File Authentication Success :: {message_suffix}")
                    return True
                _LOGGER.info(f"File Authentication Failed :: {message_suffix}")
                raise Exception(error_msg)

            if (result := self._client_id_split_helper(client_id)) is None:
                raise Exception(error_msg)
            did, class_id, resource, client_type = result

            # username has more information included
            if username and "`" in username and (username_info := username.split("`")) and len(username_info) >= 3:
                # Content example: {"fv":"1.0.0","wv":"v2.1.0"}
                user_header: str = base64.b64decode(username_info[1].replace("\n", "")).decode("utf-8")
                # Content example: {"app":"user","st":10}
                user_body: str = base64.b64decode(username_info[2].replace("\n", "")).decode("utf-8")
                session.username = username_info[0]
                username = session.username
                _LOGGER.debug(f"Bumper USER info :: {user_header!s} :: {user_body!s}")

            # Check when Password authentication is enabled
            if bumper_isc.USE_AUTH:
                if password is None:
                    _LOGGER.warning(
                        "Bumper Authentication Failed :: "
                        "No password provided and password authentication is enabled ('USE_AUTH')",
                    )
                    raise Exception(error_msg)
                if not token_repo.verify_auth_code(did, password):
                    _LOGGER.warning("Bumper Authentication Failed :: Wrong password")
                    raise Exception(error_msg)

            if username and client_type == "bot":
                bot_repo.add(username, did, class_id, resource, "eco-ng")
                _LOGGER.info(f"Bumper Authentication Success :: Bot :: Username: {username} :: ClientID: {client_id}")

                if bumper_isc.BUMPER_PROXY_MQTT and username is not None and password is not None:
                    mqtt_server = await utils.resolve(bumper_isc.PROXY_MQTT_DOMAIN)
                    _LOGGER_PROXY.info(f"MQTT Proxy Mode :: Using server {mqtt_server} for client {client_id}")
                    proxy = mqtt_proxy.ProxyClient(client_id, mqtt_server, config=ClientConfig(check_hostname=False))
                    self._proxy_clients[client_id] = proxy
                    await proxy.connect(username, password)

                return True

            # all other will add as a client
            client_repo.add(username, did, class_id, resource)
            _LOGGER.info(f"Bumper Authentication Success :: Client :: Username: {username} :: ClientID: {client_id}")
            return True
        except Exception:
            _LOGGER.exception(f"Session: {session}")

        # Check for allow anonymous
        if self._get_config_option("allow_anonymous", True):
            _LOGGER.info(f"Anonymous Authentication Success :: config allows anonymous :: Username: {username}")
            return True

        return False

    def _read_password_file(self) -> None:
        password_file = self._get_config_option("password_file", None)
        if not password_file:
            _LOGGER.warning("Configuration parameter 'password-file' not found")
            return

        try:
            with Path.open(password_file, encoding="utf-8") as file:
                _LOGGER.debug(f"Reading user database from {password_file}")
                for line in file:
                    t_line = line.strip()
                    if t_line and not t_line.startswith("#"):  # Skip empty lines and comments
                        (username, pwd_hash) = t_line.split(sep=":", maxsplit=3)
                        if username:
                            self._users[username] = pwd_hash
                            _LOGGER.debug(f"User '{username}' loaded")

            _LOGGER.debug(f"{len(self._users)} user(s) loaded from {password_file}")
        except FileNotFoundError:
            _LOGGER.warning(f"Password file {password_file} not found")
        except ValueError:
            _LOGGER.exception(f"Malformed password file '{password_file}'")
        except Exception:
            _LOGGER.exception(f"Unexpected error reading password file '{password_file}'")

    async def on_broker_message_received(self, message: IncomingApplicationMessage, client_id: str) -> None:
        """On message received."""
        try:
            topic = message.topic
            topic_split = topic.split("/")
            data_decoded: str = (
                message.data.decode("utf-8", errors="replace")
                if isinstance(message.data, bytes | bytearray)
                else str(message.data)
            )

            if len(topic_split) < 7:
                _LOGGER_PROXY.warning(f"Received message with invalid topic: {topic}")
                return

            if topic_split[6] == "helperbot":
                # Response to command
                _log__helperbot_message("Received Response", topic, data_decoded)
            elif topic_split[3] == "helperbot":
                # Helperbot sending command
                _log__helperbot_message("Send Command", topic, data_decoded)
            elif topic_split[1] == "atr":
                # Broadcast message received on atr
                _log__helperbot_message("Received Broadcast", topic, data_decoded)
            else:
                _log__helperbot_message("Received Message", topic, data_decoded)

            if bumper_isc.BUMPER_PROXY_MQTT and client_id in self._proxy_clients:
                if topic_split[3] == "proxyhelper":
                    # if from proxyhelper, don't send back to ecovacs...yet
                    return

                if topic_split[6] == "proxyhelper":
                    ttopic = topic.split("/")
                    ttopic[6] = self._proxy_clients[client_id].request_mapper.pop(ttopic[10], "")
                    if ttopic[6] == "":
                        _LOGGER_PROXY.warning(
                            "Request mapper is missing entry, probably request took to"
                            f" long... Client_id: {client_id} :: Request_id: {ttopic[10]}",
                        )
                        return

                    ttopic_join = "/".join(ttopic)
                    _LOGGER_PROXY.info(f"Bot Message Converted Topic From {topic} TO {ttopic_join} with message: {data_decoded}")
                else:
                    ttopic_join = topic
                    _LOGGER_PROXY.info(f"Bot Message From {ttopic_join} with message: {data_decoded}")

                try:
                    # Send back to ecovacs
                    _LOGGER_PROXY.info(f"Proxy Forward Message to Ecovacs :: Topic: {ttopic_join} :: Message: {data_decoded}")
                    await self._proxy_clients[client_id].publish(ttopic_join, data_decoded.encode(), message.qos)
                except Exception as e:
                    _LOGGER_PROXY.error(f"Forwarding to Ecovacs :: Exception :: {e}", exc_info=True)
        except Exception as e:
            _LOGGER_PROXY.error(f"Received message :: Exception :: {message.data} :: {e}", exc_info=True)

    async def on_broker_client_subscribed(self, client_id: str, topic: str, qos: Literal[0, 1, 2]) -> None:
        """Is called when a client subscribes on the broker."""
        _LOGGER.debug(f"MQTT Broker :: New MQTT Topic Subscription :: Client: {client_id} :: Topic: {topic}")
        if bumper_isc.BUMPER_PROXY_MQTT:
            # if proxy mode, also subscribe on ecovacs server
            if client_id in self._proxy_clients:
                await self._proxy_clients[client_id].subscribe(topic, qos)
                _LOGGER_PROXY.info(f"MQTT Proxy Mode :: New MQTT Topic Subscription :: Client: {client_id} :: Topic: {topic}")
            elif client_id != helper_bot.HELPER_BOT_CLIENT_ID:
                _LOGGER_PROXY.warning(f"MQTT Proxy Mode :: No proxy client found! :: Client: {client_id} :: Topic: {topic}")

    async def on_broker_client_connected(self, client_id: str, client_session: Session) -> None:
        """On client connected."""
        self._set_client_connected(client_id, True, client_session)

    async def on_broker_client_disconnected(self, client_id: str, client_session: Session) -> None:
        """On client disconnect."""
        if bumper_isc.BUMPER_PROXY_MQTT and client_id in self._proxy_clients:
            await self._proxy_clients.pop(client_id).disconnect()
        self._set_client_connected(client_id, False, client_session)

    def _set_client_connected(self, client_id: str, connected: bool, _: Session) -> None:
        try:
            # Skip the HelperBot
            if client_id == helper_bot.HELPER_BOT_CLIENT_ID:
                return

            if (result := self._client_id_split_helper(client_id)) is None:
                return
            did, _, __, client_type = result

            if client_type == "bot":
                if bot := bot_repo.get(did):
                    bot_repo.set_mqtt(bot.did, connected)
                    if connected:
                        asyncio.create_task(self._set_bot_timezone(did))  # noqa: RUF006
                return
            if client_type == "user":
                if client := client_repo.get(did):
                    client_repo.set_mqtt(client.userid, connected)
                return
        except Exception:
            _LOGGER.exception("Failed to connect client")

    def _client_id_split_helper(self, client_id: str) -> tuple[str, str, str, Literal["bot", "user"]] | None:
        try:
            did, rest = client_id.split("@", 1)
            class_id, resource = rest.split("/", 1)
        except ValueError:
            _LOGGER.warning(f"Failed to connect client :: Wrong formatted client_id '{client_id}'")
            return None

        # if not identified with a user class_id, we mark as bot
        client_type: Literal["bot", "user"] = "user" if class_id in bumper_isc.USER_REALMS else "bot"
        return did, class_id, resource, client_type

    async def _set_bot_timezone(self, did: str) -> None:
        """Set bot timezone, sync on connect."""
        try:
            if bumper_isc.SYNC_TIMEZONE is False:
                return
            if bumper_isc.mqtt_helperbot is None:
                msg = "'bumper_isc.mqtt_helperbot' is None"
                raise Exception(msg)
            if not (bot := bot_repo.get(did)):
                return

            offset_minutes, timestamp_s = utils.get_tzm_and_ts()
            timestamp_s_ts = timestamp_s * 1000
            timestamp_s_bd = timestamp_s * 1_000_000

            json_body = {
                "cmdName": "setTimeZone",
                "toId": bot.did,
                "toType": bot.class_id,
                "toRes": bot.resource,
                "payload": {
                    "header": {
                        "pri": 2,
                        "ts": str(timestamp_s_ts),
                        "tzm": offset_minutes,
                        "ver": "0.0.22",
                    },
                    "body": {
                        "data": {
                            "tzm": offset_minutes,
                            "bdTaskID": str(timestamp_s_bd),
                        },
                    },
                },
            }
            cmd_request = helper_bot.MQTTCommandModel(cmdjson=json_body, version="1")
            _LOGGER.info(
                f"Syncing timezone for bot {bot.did}: "
                f"tzm={offset_minutes} :: ts={timestamp_s_ts} :: bdTaskID={timestamp_s_bd} "
                f"({datetime.fromtimestamp(timestamp_s, tz=bumper_isc.LOCAL_TIMEZONE).strftime('%Y-%m-%d %H:%M')})",
            )

            await bumper_isc.mqtt_helperbot.send_command(cmd_request)
        except Exception:
            _LOGGER.exception("Failed to set timezone on bot")
