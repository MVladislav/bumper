import asyncio
from pathlib import Path
import ssl
from unittest import mock

from aiomqtt import Client
from amqtt.session import IncomingApplicationMessage, Session
import pytest
from testfixtures import LogCapture

from bumper.db import client_repo, user_repo
from bumper.mqtt.server import BumperMQTTServerPlugin, MQTTBinding, MQTTServer, _log__helperbot_message, mqtt_proxy
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from tests import HOST, MQTT_PORT

from .mqtt_util import verify_subscribe

_LOGGER_NAME = "bumper.mqtt.server"


def async_return(result: str | bool | None) -> asyncio.Future:
    """Return an async result."""
    f = asyncio.Future()
    f.set_result(result)
    return f


def test_log__helperbot_message() -> None:
    """Test logging helper bot messages."""
    custom_log_message = "custom_log_message"
    topic = "topic"
    data = "data"
    with LogCapture() as log:
        _log__helperbot_message(custom_log_message, topic, data)
        log.check_present(
            (
                f"{_LOGGER_NAME}.messages",
                "DEBUG",
                f"{custom_log_message} :: Topic: {topic} :: Message: {data}",
            ),
            order_matters=False,
        )


@pytest.mark.usefixtures("clean_database", "mqtt_server_anonymous")
@pytest.mark.parametrize("proxy", [False, True])
async def test_mqttserver(proxy: bool) -> None:
    """Test MQTT server functionality."""
    bumper_isc.BUMPER_PROXY_MQTT = proxy

    # Test client connect
    user_repo.add("user_123")  # Add user to db
    client_repo.add("bumper", "user_123", "ecouser.net", "resource_123")  # Add client to db

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="user_123@ecouser.net/resource_123",
    ) as client:
        # Verify connection by subscribing and publishing a message
        mock_callback = mock.Mock()
        await verify_subscribe(
            client,
            did="user_123",
            device_class="test_class",
            resource="test_resource",
            mock=mock_callback,
            expected_called=True,
        )

    # Test fake_bot connect
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="bot_serial@ls1ok3/wC3g",
    ) as client:
        # Verify connection by subscribing and publishing a message
        mock_callback = mock.Mock()
        await verify_subscribe(
            client,
            did="bot_serial",
            device_class="test_class",
            resource="test_resource",
            mock=mock_callback,
            expected_called=True,
        )

    # Test file auth client connect
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="test-file-auth",
        username="test-client",
        password="abc123!",  # noqa: S106
    ) as client:
        # Verify connection by subscribing and publishing a message
        mock_callback = mock.Mock()
        await verify_subscribe(
            client,
            did="test-file-auth",
            device_class="test_class",
            resource="test_resource",
            mock=mock_callback,
            expected_called=True,
        )

    with LogCapture() as log:
        # Bad password
        async with Client(
            hostname=HOST,
            port=MQTT_PORT,
            tls_context=ssl_ctx,
            identifier="test-file-auth",
            username="test-client",
            password="notvalid!",  # noqa: S106
        ):
            pass

        log.check_present(
            (
                _LOGGER_NAME,
                "INFO",
                "File Authentication Failed :: Username: test-client - ClientID: test-file-auth",
            ),
            order_matters=False,
        )
        log.clear()

        # No username in file
        async with Client(
            hostname=HOST,
            port=MQTT_PORT,
            tls_context=ssl_ctx,
            identifier="test-file-auth",
            username="test-client-noexist",
            password="notvalid!",  # noqa: S106
        ):
            pass

        log.check_present(
            (
                _LOGGER_NAME,
                "INFO",
                "File Authentication Failed :: No Entry for :: Username: test-client-noexist - ClientID: test-file-auth",
            ),
            order_matters=False,
        )
        log.clear()

        # Test proxy
        if proxy:
            utils.resolve = mock.MagicMock(return_value=async_return("127.0.0.1"))
            mqtt_proxy.ProxyClient.connect = mock.MagicMock(return_value=async_return(True))
            mqtt_proxy.ProxyClient.disconnect = mock.MagicMock(return_value=async_return(True))
            mqtt_proxy.ProxyClient.subscribe = mock.MagicMock(return_value=async_return(None))
            mqtt_proxy.ProxyClient.publish = mock.MagicMock(return_value=async_return(None))

            async with Client(
                hostname=HOST,
                port=MQTT_PORT,
                tls_context=ssl_ctx,
                identifier="user_123@ls1ok3/wC3g",
                username="user_123",
                password="abc123!",  # noqa: S106
            ) as client:
                # Verify connection by subscribing and publishing a message
                mock_callback = mock.Mock()
                await verify_subscribe(
                    client,
                    did="user_123",
                    device_class="test_class",
                    resource="test_resource",
                    mock=mock_callback,
                    expected_called=True,
                )

            log.check_present(
                (
                    _LOGGER_NAME,
                    "INFO",
                    "Bumper Authentication Success :: Bot :: Username: user_123 :: ClientID: user_123@ls1ok3/wC3g",
                ),
                order_matters=False,
            )

            log.check_present(
                (
                    f"{_LOGGER_NAME}.proxy",
                    "INFO",
                    "MQTT Proxy Mode :: Using server 127.0.0.1 for client user_123@ls1ok3/wC3g",
                ),
                order_matters=False,
            )
    bumper_isc.BUMPER_PROXY_MQTT = False


@pytest.mark.usefixtures("clean_database", "mqtt_server_anonymous")
@pytest.mark.parametrize("proxy", [False])
async def test_mqttserver_subscribe(proxy: bool) -> None:
    """Test MQTT server subscription."""
    with LogCapture() as log:
        bumper_isc.BUMPER_PROXY_MQTT = proxy
        if proxy:
            utils.resolve = mock.MagicMock(return_value=async_return("127.0.0.1"))

        user_repo.add("user_123")  # Add user to db
        client_repo.add("bumper", "user_123", "ecouser.net", "resource_123")  # Add client to db

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        async with Client(
            hostname=HOST,
            port=MQTT_PORT,
            tls_context=ssl_ctx,
            identifier="user_123@ls1ok3/wC3g",
            username="user_123",
            password="abc123!",  # noqa: S106
        ) as client:
            log.clear()
            await client.subscribe("iot/atr/+/+/+/+/+")
            await asyncio.sleep(0.1)

        log.check_present(
            (
                _LOGGER_NAME,
                "DEBUG",
                "MQTT Broker :: New MQTT Topic Subscription :: Client: user_123@ls1ok3/wC3g :: Topic: iot/atr/+/+/+/+/+",
            ),
            order_matters=False,
        )
    bumper_isc.BUMPER_PROXY_MQTT = False


async def test_mqttserver_no_file_auth() -> None:
    """Test MQTT server with no password file."""
    with LogCapture() as log:
        mqtt_server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True), password_file="tests/_test_files/passwd-notfound")  # noqa: S106
        await mqtt_server.start()
        try:
            log.check_present(
                (
                    _LOGGER_NAME,
                    "WARNING",
                    "Password file tests/_test_files/passwd-notfound not found",
                ),
                order_matters=False,
            )
        finally:
            await mqtt_server.shutdown()


async def test_mqttserver_default_pw_file_double_start() -> None:
    """Test MQTT server double start with default password file."""
    with LogCapture() as log:
        mqtt_server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True))
        try:
            await mqtt_server.start()
            log.check_present(
                (
                    _LOGGER_NAME,
                    "INFO",
                    f"Starting MQTT Server at {HOST}:{MQTT_PORT}",
                ),
                order_matters=False,
            )

            log.clear()

            await mqtt_server.start()
            log.check_present(
                (
                    _LOGGER_NAME,
                    "INFO",
                    "MQTT Server is already running. Stop it first for a clean restart!",
                ),
                order_matters=False,
            )
        finally:
            await mqtt_server.shutdown()


async def test_mqttserver_shutdown() -> None:
    """Test MQTT server shutdown."""
    with LogCapture() as log:
        mqtt_server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True))
        try:
            await mqtt_server.start()

            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            async with Client(
                hostname=HOST,
                port=MQTT_PORT,
                tls_context=ssl_ctx,
                identifier="user_123@ecouser.net/resource_123",
            ) as client:
                # Verify connection by publishing a test message
                await client.publish("test/topic", b"test message")

        finally:
            log.clear()
            handlers = [handler for (_, handler) in mqtt_server._broker._sessions.values()]
            assert len(handlers) > 0
            await mqtt_server.shutdown()
            handlers = [handler for (_, handler) in mqtt_server._broker._sessions.values()]
            assert len(handlers) == 0

            log.check_present(
                (
                    f"{_LOGGER_NAME}.broker",
                    "INFO",
                    "Broker closed",
                ),
                order_matters=False,
            )

            log.clear()
            await mqtt_server.shutdown()
            log.check_present(
                (
                    _LOGGER_NAME,
                    "WARNING",
                    f"MQTT server is not in a valid state for shutdown. Current state: {mqtt_server.state}",
                ),
                order_matters=False,
            )


class _FakeContext:
    """Minimal stand-in for a plugin context backed by the plugin's Config dataclass."""

    def __init__(self, password_file: str, allow_anonymous: bool) -> None:
        self.config: BumperMQTTServerPlugin.Config = BumperMQTTServerPlugin.Config(
            allow_anonymous=allow_anonymous,
            password_file=password_file,
        )
        self.logger = mock.MagicMock()


def _make_plugin(password_file: str, allow_anonymous: bool = False) -> BumperMQTTServerPlugin:
    """Build a BumperMQTTServerPlugin with a lightweight fake context."""
    return BumperMQTTServerPlugin(_FakeContext(password_file, allow_anonymous))


@pytest.mark.parametrize(
    "passwd_line",
    [
        "$6$e9026a738b07b5a1$WaoYMI61aIPhhjfe3FG3uzV1oqyRdLi/TvLbBbvvzFyJ7T6PrileHGkzKkJUMLGQm/dhcq0fUT8mcu2kVcjbX/",
        "not-a-hash",
    ],
)
async def test_file_auth_unsupported_hash_rejected(tmp_path: Path, passwd_line: str) -> None:
    """Legacy/unknown hash formats must not authenticate after the pwdlib (argon2) migration."""
    passwd = tmp_path / "passwd"
    passwd.write_text(f"{'test-user'}:{passwd_line}\n")
    plugin = _make_plugin(str(passwd), allow_anonymous=False)

    session = Session()
    session.username = "test-user"
    session.password = "abc123!"  # noqa: S105
    session.client_id = "test-file-auth"

    with mock.patch("bumper.mqtt.server.bot_repo.add"), mock.patch("bumper.mqtt.server.client_repo.add"):
        result = await plugin.authenticate(session=session)

    assert result is False


async def test_file_auth_valid_argon2_success(tmp_path: Path) -> None:
    """A valid argon2 hash authenticates after the pwdlib migration."""
    passwd = tmp_path / "passwd"
    passwd.write_text(
        "test-user:$argon2id$v=19$m=65536,t=3,p=4$C0YnfmmfIWjbVgectg+kaA$VdMaeiMDqY66RXKFKYglW8bQ7ZU5om1Ms3zxXBHVXak\n",
    )
    plugin = _make_plugin(str(passwd), allow_anonymous=False)

    session = Session()
    session.username = "test-user"
    session.password = "abc123!"  # noqa: S105
    session.client_id = "test-file-auth"

    assert await plugin.authenticate(session=session) is True


async def test_on_broker_message_received_proxy_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A hanging proxy publish is bounded by PROXY_PUBLISH_TIMEOUT and does not block."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    monkeypatch.setattr(bumper_isc, "PROXY_PUBLISH_TIMEOUT", 0.05)

    plugin = _make_plugin(str(tmp_path / "passwd"))

    async def _never_returns(_topic: str, _message: bytes, _qos: int | None) -> None:
        await asyncio.sleep(60)

    proxy = mock.AsyncMock()
    proxy.publish = mock.AsyncMock(side_effect=_never_returns)
    plugin._proxy_clients["user_123@ls1ok3/wC3g"] = proxy

    msg = IncomingApplicationMessage(None, "iot/atr/test/user_123/ls1ok3/wC3g/j", 0, b"payload", False)

    # Must return promptly (bounded by the timeout), not hang for the full sleep(60).
    await asyncio.wait_for(
        plugin.on_broker_message_received(msg, "user_123@ls1ok3/wC3g"),
        timeout=2.0,
    )
    proxy.publish.assert_awaited_once()
