"""MQTT Server module."""

import asyncio
import dataclasses
import logging
from pathlib import Path
from typing import Any, Literal

from amqtt.broker import Broker, BrokerContext
from amqtt.mqtt.protocol.broker_handler import BrokerProtocolHandler
from amqtt.session import IncomingApplicationMessage, Session
from passlib.apps import custom_app_context as pwd_context

from bumper.mqtt import helper_bot, proxy as mqtt_proxy
from bumper.utils import db, dns, utils
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

            # self._add_entry_point()

            config_bind = {"default": {"type": "tcp"}}
            listener_prefix = "mqtt"
            for index, binding in enumerate(self._bindings):
                config_bind[f"{listener_prefix}{index}"] = {
                    "bind": f"{binding.host}:{binding.port}",
                    "ssl": "on" if binding.use_ssl is True else "off",
                }
                if binding.use_ssl is True:
                    config_bind[f"{listener_prefix}{index}"]["cafile"] = str(bumper_isc.ca_cert)
                    config_bind[f"{listener_prefix}{index}"]["certfile"] = str(bumper_isc.server_cert)
                    config_bind[f"{listener_prefix}{index}"]["keyfile"] = str(bumper_isc.server_key)

            # Initialize bot server
            config = {
                "listeners": config_bind,
                "sys_interval": 0,
                "auth": {
                    "allow-anonymous": allow_anonymous,
                    "password-file": password_file,
                    "plugins": ["bumper"],  # Bumper plugin provides auth and handling of bots/clients connecting
                },
            }

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
        # pylint: disable-next=protected-access
        return [session for (session, _) in self._broker._sessions.values()]  # noqa: SLF001

    @property
    def handlers(self) -> list[BrokerProtocolHandler]:
        """Get handlers."""
        # pylint: disable-next=protected-access
        return [handler for (_, handler) in self._broker._sessions.values()]  # noqa: SLF001

    async def start(self) -> None:
        """Start MQTT server."""
        try:
            if self.state not in ["stopping", "starting", "started"]:
                for binding in self._bindings:
                    _LOGGER.info(f"Starting MQTT Server at {binding.host}:{binding.port}")
                await self._broker.start()
            elif self.state == "stopping":
                _LOGGER.warning("MQTT Server is stopping. Waiting for it to stop before restarting...")
                state_changed_event = asyncio.Event()

                def state_change_callback() -> None:
                    if self.state != "stopping":
                        state_changed_event.set()

                self._broker.transitions.add_callback(state_change_callback)
                try:
                    await state_changed_event.wait()
                finally:
                    self._broker.transitions.remove_callback(state_change_callback)
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
                # Stop session handlers manually; handle exceptions more gracefully
                for handler in self.handlers:
                    try:
                        await handler.stop()
                    except Exception:
                        _LOGGER.exception("Error stopping session handler")

                await self._broker.shutdown()
                _LOGGER_BROKER.info("Broker closed")
            elif self.state in ["stopping", "starting"]:
                _LOGGER.warning(f"MQTT server is in '{self.state}' state. Waiting for it to stabilize...")
                while self.state in ["stopping", "starting"]:  # noqa: ASYNC110
                    await asyncio.sleep(0.1)
                if self.state == "started":
                    await self.shutdown()
            else:
                _LOGGER.warning(f"MQTT server is not in a valid state for shutdown. Current state: {self.state}")
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during shutdown"))
            raise


class BumperMQTTServerPlugin:
    """MQTT Server plugin which handles the authentication."""

    def __init__(self, context: BrokerContext) -> None:
        """MQTT Server plugin init."""
        self._proxy_clients: dict[str, mqtt_proxy.ProxyClient] = {}
        self.context = context
        try:
            if self.context.config is not None:
                self.auth_config = self.context.config["auth"]
                self._users: dict[str, str] = self._read_password_file()
            else:
                msg = "context config is not set"
                raise Exception(msg)
        except KeyError:
            _LOGGER.warning("'bumper' section not found in context configuration")
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during plugin initialization"))
            raise

    async def authenticate(self, session: Session, **kwargs: dict[str, Any]) -> bool:
        """Authenticate session."""
        username: str | None = session.username
        password: str | None = session.password
        client_id: str | None = session.client_id

        try:
            # Auth the HelperBot
            if client_id == helper_bot.HELPER_BOT_CLIENT_ID:
                if bumper_isc.INFO_LOGGING_VERBOSE:
                    _LOGGER.info(f"Bumper Authentication Success :: Helperbot :: {client_id}")
                return True

            if client_id and "@" in client_id:
                client_id_split = client_id.split("@")
                client_details_split = client_id_split[1].split("/")
                tmp_bot_client_info: str = client_id_split[1]
                tmp_did: str = client_id_split[0]
                tmp_dev_class: str = client_details_split[0]
                tmp_resource: str = client_details_split[1]

                # if ecouser or bumper aren't in details it is a bot
                if username is not None and "ecouser" not in tmp_bot_client_info and "bumper" not in tmp_bot_client_info:
                    db.bot_add(username, tmp_did, tmp_dev_class, tmp_resource, "eco-ng")
                    if bumper_isc.INFO_LOGGING_VERBOSE:
                        _LOGGER.info(
                            f"Bumper Authentication Success :: Bot :: SN: {username} :: DID: {tmp_did} :: Class: {tmp_dev_class}",
                        )

                    if bumper_isc.BUMPER_PROXY_MQTT and password is not None:
                        mqtt_server = await dns.resolve(bumper_isc.PROXY_MQTT_DOMAIN)
                        _LOGGER_PROXY.info(f"MQTT Proxy Mode :: Using server {mqtt_server} for client {client_id}")
                        proxy = mqtt_proxy.ProxyClient(client_id, mqtt_server, config={"check_hostname": False})
                        self._proxy_clients[client_id] = proxy
                        await proxy.connect(username, password)
                    return True

                if (password is not None and db.check_auth_code(tmp_did, password)) or not bumper_isc.USE_AUTH:
                    db.client_add(tmp_did, tmp_dev_class, tmp_resource)
                    if bumper_isc.INFO_LOGGING_VERBOSE:
                        _LOGGER.info(f"Bumper Authentication Success :: Client :: Username: {username} :: ClientID: {client_id}")
                    return True

            # Check for File Auth
            if username is not None and password is not None:
                # If there is a username and it isn't already authenticated
                password_hash = self._users.get(username)
                message_suffix = f"Username: {username} - ClientID: {client_id}"

                if password_hash is None:  # If there is a matching entry in passwd, check hash
                    _LOGGER.info(f"File Authentication Failed :: No Entry for :: {message_suffix}")

                if pwd_context.verify(password, password_hash):
                    _LOGGER.info(f"File Authentication Success :: {message_suffix}")
                    return True

                _LOGGER.info(f"File Authentication Failed :: {message_suffix}")
        except Exception:
            _LOGGER.exception(f"Session: {kwargs.get('session', '')}")

        # Check for allow anonymous
        if self.auth_config.get("allow-anonymous", True):
            _LOGGER.info(f"Anonymous Authentication Success: config allows anonymous :: Username: {username}")
            return True

        return False

    def _read_password_file(self) -> dict[str, str]:
        password_file = self.auth_config.get("password-file")
        users: dict[str, str] = {}
        if password_file:
            try:
                with Path.open(password_file, encoding="utf-8") as file:
                    _LOGGER.debug(f"Reading user database from {password_file}")
                    for line in file:
                        t_line = line.strip()
                        if not t_line.startswith("#"):  # Allow comments in files
                            (username, pwd_hash) = t_line.split(sep=":", maxsplit=3)
                            if username:
                                users[username] = pwd_hash
                                _LOGGER.debug(f"user: {username} :: hash: {pwd_hash}")

                _LOGGER.debug(f"{(len(users))} user(s) read from file {password_file}")
            except FileNotFoundError:
                _LOGGER.warning(f"Password file {password_file} not found")

        return users

    async def on_broker_message_received(self, message: IncomingApplicationMessage, client_id: str) -> None:
        """On message received."""
        try:
            topic = message.topic
            topic_split = topic.split("/")
            data_decoded = (
                message.data.decode("utf-8", errors="replace") if isinstance(message.data, bytes | bytearray) else message.data
            )

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

    async def on_broker_client_connected(self, client_id: str) -> None:
        """On client connected."""
        self._set_client_connected(client_id, True)

    async def on_broker_client_disconnected(self, client_id: str) -> None:
        """On client disconnect."""
        if bumper_isc.BUMPER_PROXY_MQTT and client_id in self._proxy_clients:
            await self._proxy_clients.pop(client_id).disconnect()
        self._set_client_connected(client_id, False)

    def _set_client_connected(self, client_id: str, connected: bool) -> None:
        try:
            didsplit = client_id.split("@")
            bot = db.bot_get(didsplit[0])
            if bot is not None:
                db.bot_set_mqtt(bot.get("did"), connected)
                return

            clientresource = didsplit[1].split("/")[1]
            client = db.client_get(clientresource)
            if client:
                db.client_set_mqtt(client["resource"], connected)
        except Exception:
            _LOGGER.exception("Failed to connect client")
