import asyncio
import base64
from pathlib import Path
import ssl
from unittest import mock

from aiomqtt import Client
from amqtt.session import IncomingApplicationMessage, Session
import pytest
from testfixtures import LogCapture

from bumper.db import client_repo, token_repo, user_repo
from bumper.mqtt import server as server_module
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
        identifier="bot_serial@class_x/res2",
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
                identifier="user_123@class_x/res2",
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
                    "Bumper Authentication Success :: Bot :: Username: user_123 :: ClientID: user_123@class_x/res2",
                ),
                order_matters=False,
            )

            log.check_present(
                (
                    f"{_LOGGER_NAME}.proxy",
                    "INFO",
                    "MQTT Proxy Mode :: Using server 127.0.0.1 for client user_123@class_x/res2",
                ),
                order_matters=False,
            )
    bumper_isc.BUMPER_PROXY_MQTT = False


@pytest.mark.usefixtures("clean_database", "mqtt_server_anonymous")
async def test_mqtt_client_resolves_transport_name_to_account() -> None:
    """The auth code names the account, so the old client name is merged."""
    user_repo.add("canonical")
    token_repo.add("canonical", "token")
    token_repo.add_auth_code("canonical", "auth-code")
    client_repo.add("app", "legacy", "realm", "resource")

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="legacy@USER/resource",
        username="app",
        password="auth-code",  # noqa: S106
    ):
        pass

    client = client_repo.get("legacy")
    assert client is not None
    assert client.userid == "canonical"
    assert len(client_repo.list_all()) == 1


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
            identifier="user_123@class_x/res2",
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
                "MQTT Broker :: New MQTT Topic Subscription :: Client: user_123@class_x/res2 :: Topic: iot/atr/+/+/+/+/+",
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


async def test_mqttserver_shutdown_with_a_client_that_does_not_go(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The server stops even when a client stays connected.

    The broker waits for the clients that are still connected, and a robot that
    is online never says goodbye. The server has to stop anyway, or it stays
    down for good.
    """
    monkeypatch.setattr(server_module, "SHUTDOWN_TIMEOUT", 0.1)
    mqtt_server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True))
    shutdown = mqtt_server._broker.shutdown
    try:
        await mqtt_server.start()

        # A broker that hangs while it stops, like one with a client that
        # stays connected.
        async def _hanging_shutdown() -> None:
            mqtt_server._broker.transitions.shutdown()
            await asyncio.sleep(60)

        mqtt_server._broker.shutdown = _hanging_shutdown

        await mqtt_server.shutdown()

        assert mqtt_server.state == "stopped"
    finally:
        mqtt_server._broker.shutdown = shutdown
        # The broker never closed its listener, so it is closed here.
        for server in mqtt_server._broker._servers.values():
            await server.close_instance()
        await mqtt_server.shutdown()


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
    plugin._proxy_clients["user_123@class_x/res2"] = proxy

    msg = IncomingApplicationMessage(None, "iot/atr/test/user_123/class_x/res2/j", 0, b"payload", False)

    # Must return promptly (bounded by the timeout), not hang for the full sleep(60).
    await asyncio.wait_for(
        plugin.on_broker_message_received(msg, "user_123@class_x/res2"),
        timeout=2.0,
    )
    proxy.publish.assert_awaited_once()


async def test_authenticate_no_client_id() -> None:
    """Missing client_id fails authentication."""
    plugin = _make_plugin(None, allow_anonymous=False)  # type: ignore[arg-type]

    session = Session()
    session.username = "user"
    session.password = "secret"  # noqa: S105
    session.client_id = None

    assert await plugin.authenticate(session=session) is False


async def test_client_id_split_helper_none() -> None:
    """A client id without '@' that is not a file-auth client cannot be split."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]

    assert plugin._client_id_split_helper("noatsign") is None


async def test_authenticate_split_helper_none_branch(tmp_path: Path) -> None:
    """authenticate returns False when the client id cannot be split."""
    plugin = _make_plugin(str(tmp_path / "passwd"), allow_anonymous=False)

    session = Session()
    session.username = None
    session.password = None
    session.client_id = "noatsign"

    assert await plugin.authenticate(session=session) is False


async def test_authenticate_resolves_transport_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolved transport name differing from the did is logged."""
    monkeypatch.setattr(
        server_module.identity,
        "resolve_transport_user",
        lambda _transport_id, _secret: mock.MagicMock(userid="canonical"),
    )

    plugin = _make_plugin(str(tmp_path / "passwd"), allow_anonymous=False)

    session = Session()
    session.username = "app"
    session.password = "secret"  # noqa: S105
    session.client_id = "legacy@USER/resource"

    with mock.patch("bumper.mqtt.server.client_repo.add"):
        result = await plugin.authenticate(session=session)

    assert result is True


async def test_authenticate_username_backticks(tmp_path: Path) -> None:
    """A username carrying base64 header/body info is decoded."""
    header = base64.b64encode(b'{"fv":"1.0.0"}').decode()
    body = base64.b64encode(b'{"app":"user"}').decode()
    username = f"realuser`{header}`{body}"

    plugin = _make_plugin(str(tmp_path / "passwd"), allow_anonymous=True)

    session = Session()
    session.username = username
    session.password = None
    session.client_id = "did@ecouser.net/res"

    with mock.patch("bumper.mqtt.server.client_repo.add"):
        result = await plugin.authenticate(session=session)

    assert result is True
    assert session.username == "realuser"


async def test_authenticate_use_auth_no_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """USE_AUTH with no password fails authentication."""
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    plugin = _make_plugin(str(tmp_path / "passwd"), allow_anonymous=False)

    session = Session()
    session.username = "app"
    session.password = None
    session.client_id = "did@ecouser.net/res"

    assert await plugin.authenticate(session=session) is False


async def test_authenticate_use_auth_wrong_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """USE_AUTH with a wrong password fails authentication."""
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    monkeypatch.setattr(server_module.identity, "verify_transport_secret", lambda _user_id, _secret: False)
    plugin = _make_plugin(str(tmp_path / "passwd"), allow_anonymous=False)

    session = Session()
    session.username = "app"
    session.password = "wrong"  # noqa: S105
    session.client_id = "did@ecouser.net/res"

    assert await plugin.authenticate(session=session) is False


async def test_read_password_file_missing(tmp_path: Path) -> None:
    """A missing password file logs a warning."""
    plugin = _make_plugin(str(tmp_path / "does-not-exist"))

    assert plugin._users == {}


async def test_read_password_file_none() -> None:
    """A None password file logs a warning and loads no users."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]

    assert plugin._users == {}


async def test_read_password_file_malformed(tmp_path: Path) -> None:
    """A malformed password file is handled."""
    passwd = tmp_path / "passwd"
    passwd.write_text("badline-no-colon\n")
    plugin = _make_plugin(str(passwd))

    assert plugin._users == {}


async def test_read_password_file_unexpected(tmp_path: Path) -> None:
    """An unexpected error reading the password file is handled."""
    plugin = _make_plugin(str(tmp_path))

    assert plugin._users == {}


async def test_on_broker_message_received_proxyhelper_topic3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A message whose third-ish segment is proxyhelper returns early."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    plugin = _make_plugin(str(tmp_path / "passwd"))
    proxy = mock.AsyncMock()
    plugin._proxy_clients["cid"] = proxy

    topic = "a/b/c/proxyhelper/d/e/f/g"
    msg = IncomingApplicationMessage(None, topic, 0, b"payload", False)

    await plugin.on_broker_message_received(msg, "cid")

    proxy.publish.assert_not_awaited()


async def test_on_broker_message_received_proxyhelper_topic6_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing request mapper entry logs a warning and returns."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    plugin = _make_plugin(str(tmp_path / "passwd"))
    proxy = mock.AsyncMock()
    proxy.request_mapper = {}
    plugin._proxy_clients["cid"] = proxy

    topic = "a/rid/c/d/e/f/proxyhelper/g/h/i/reqkey/k"
    msg = IncomingApplicationMessage(None, topic, 0, b"payload", False)

    with LogCapture() as log:
        await plugin.on_broker_message_received(msg, "cid")
        log.check_present(
            (
                f"{_LOGGER_NAME}.proxy",
                "WARNING",
                "Request mapper is missing entry, probably request took to long... Client_id: cid :: Request_id: reqkey",
            ),
            order_matters=False,
        )

    proxy.publish.assert_not_awaited()


async def test_on_broker_message_received_proxyhelper_topic6_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A present request mapper entry converts the topic and forwards."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    plugin = _make_plugin(str(tmp_path / "passwd"))
    proxy = mock.AsyncMock()
    proxy.request_mapper = {"reqkey": "orig"}
    plugin._proxy_clients["cid"] = proxy

    topic = "a/rid/c/d/e/f/proxyhelper/g/h/i/reqkey/k"
    msg = IncomingApplicationMessage(None, topic, 0, b"payload", False)

    await plugin.on_broker_message_received(msg, "cid")

    proxy.publish.assert_awaited_once()


async def test_on_broker_message_received_proxy_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception while forwarding to Ecovacs is logged."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    plugin = _make_plugin(str(tmp_path / "passwd"))
    proxy = mock.AsyncMock()
    proxy.publish = mock.AsyncMock(side_effect=RuntimeError("boom"))
    proxy.request_mapper = {}
    plugin._proxy_clients["cid"] = proxy

    topic = "iot/atr/test/user/class/res/j"
    msg = IncomingApplicationMessage(None, topic, 0, b"payload", False)

    await plugin.on_broker_message_received(msg, "cid")

    proxy.publish.assert_awaited_once()


async def test_on_broker_client_disconnected_proxy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Disconnecting a proxied client pops and disconnects the proxy."""
    monkeypatch.setattr(bumper_isc, "BUMPER_PROXY_MQTT", True)
    plugin = _make_plugin(str(tmp_path / "passwd"))
    proxy = mock.AsyncMock()
    plugin._proxy_clients["cid"] = proxy

    await plugin.on_broker_client_disconnected("cid", Session())

    assert "cid" not in plugin._proxy_clients
    proxy.disconnect.assert_awaited_once()


async def test_set_client_connected_user_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """A user client id updates the client repo."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]

    fake_client = mock.MagicMock(userid="uid")
    monkeypatch.setattr(server_module.client_repo, "get", lambda _did, resource=None: fake_client)  # noqa: ARG005
    monkeypatch.setattr(server_module.client_repo, "set_mqtt", mock.MagicMock())

    plugin._set_client_connected("did@USER/res", True, Session())

    server_module.client_repo.set_mqtt.assert_called_once()


async def test_set_client_connected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception while setting connected state is logged."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]

    def _raise(_did: str) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(server_module.bot_repo, "get", _raise)

    plugin._set_client_connected("did@botclass/res", True, Session())


async def test_set_bot_timezone_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting the bot timezone sends a command."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]
    monkeypatch.setattr(bumper_isc, "SYNC_TIMEZONE", True)
    helper = mock.AsyncMock()
    monkeypatch.setattr(bumper_isc, "mqtt_helperbot", helper)
    monkeypatch.setattr(server_module.bot_repo, "get", lambda did: mock.MagicMock(did=did, class_id="class", resource="res"))
    monkeypatch.setattr(server_module.utils, "get_tzm_and_ts", lambda: (60, 1000))

    await plugin._set_bot_timezone("did")

    helper.send_command.assert_awaited_once()


async def test_set_bot_timezone_disabled() -> None:
    """Disabled timezone sync returns early."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]
    bumper_isc.SYNC_TIMEZONE = False
    await plugin._set_bot_timezone("did")
    bumper_isc.SYNC_TIMEZONE = True


async def test_set_bot_timezone_no_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing helperbot is handled."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]
    monkeypatch.setattr(bumper_isc, "SYNC_TIMEZONE", True)
    monkeypatch.setattr(bumper_isc, "mqtt_helperbot", None)

    await plugin._set_bot_timezone("did")


async def test_set_bot_timezone_no_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing bot returns early."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]
    monkeypatch.setattr(bumper_isc, "SYNC_TIMEZONE", True)
    monkeypatch.setattr(bumper_isc, "mqtt_helperbot", mock.AsyncMock())
    monkeypatch.setattr(server_module.bot_repo, "get", lambda _did: None)

    await plugin._set_bot_timezone("did")


async def test_mqttserver_init_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructor failure is logged and re-raised."""

    def _raise(*_args: object, **_kwargs: object) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(server_module, "Broker", _raise)

    with pytest.raises(RuntimeError):
        MQTTServer(MQTTBinding(HOST, MQTT_PORT, True))


def _fake_mqtt_server() -> MQTTServer:
    """Build an MQTTServer whose broker is a lightweight mock."""
    server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True))
    server._broker = mock.MagicMock()
    server._broker.transitions.state = "new"
    return server


async def test_start_from_stopping_state() -> None:
    """Starting while stopping waits and forces stopping_success."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "stopping"
    server.wait_for_state_change = mock.AsyncMock()

    await server.start()

    server.wait_for_state_change.assert_awaited_once()
    server._broker.transitions.stopping_success.assert_called_once()


async def test_start_from_invalid_state() -> None:
    """Starting from an unexpected state logs a warning and does nothing."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "starting"

    await server.start()

    server._broker.start.assert_not_called()


async def test_start_exception() -> None:
    """An exception during broker start is logged and re-raised."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "new"

    async def _raise_start() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    server._broker.start = _raise_start

    with pytest.raises(RuntimeError):
        await server.start()


async def test_shutdown_from_starting_state() -> None:
    """Shutdown while starting waits and shuts down if it reaches started."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "starting"

    async def _wait(_desired: str, **_kwargs: object) -> None:
        server._broker.transitions.state = "started"

    server.wait_for_state_change = _wait
    server._broker.shutdown = mock.AsyncMock()

    await server.shutdown()

    server._broker.shutdown.assert_awaited_once()


async def test_shutdown_from_stopping_state() -> None:
    """Shutdown while stopping just waits for it to stabilize."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "stopping"
    server.wait_for_state_change = mock.AsyncMock()

    await server.shutdown()

    server.wait_for_state_change.assert_awaited_once()


async def test_shutdown_from_invalid_state() -> None:
    """Shutdown from an unexpected state logs a warning."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "new"

    with LogCapture() as log:
        await server.shutdown()
        log.check_present(
            (
                _LOGGER_NAME,
                "WARNING",
                f"MQTT server is not in a valid state for shutdown. Current state: {server.state}",
            ),
            order_matters=False,
        )


async def test_shutdown_exception() -> None:
    """An exception during broker shutdown is logged and re-raised."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "started"

    async def _raise_shutdown() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    server._broker.shutdown = _raise_shutdown

    with pytest.raises(RuntimeError):
        await server.shutdown()


async def test_wait_for_state_change_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wait that never resolves logs a timeout warning."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "started"

    async def _no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    with LogCapture() as log:
        await server.wait_for_state_change("stopped", max_wait=0.0)
        log.check_present(
            (
                _LOGGER_NAME,
                "WARNING",
                f"Timeout waiting for MQTT server to reach state 'stopped' :: Current state: '{server.state}'",
            ),
            order_matters=False,
        )


async def test_wait_for_state_change_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wait that resolves logs the reached-state debug line."""
    server = _fake_mqtt_server()
    server._broker.transitions.state = "started"

    async def _sleep_and_flip(_delay: float) -> None:
        server._broker.transitions.state = "stopped"

    monkeypatch.setattr(asyncio, "sleep", _sleep_and_flip)

    with LogCapture() as log:
        await server.wait_for_state_change("stopped", max_wait=1.0)
        log.check_present(
            (
                _LOGGER_NAME,
                "DEBUG",
                f"Reached state :: '{server.state}' == 'stopped'",
            ),
            order_matters=False,
        )


async def test_set_client_connected_bot_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bot client id updates the bot repo and schedules timezone sync."""
    plugin = _make_plugin(None)  # type: ignore[arg-type]

    fake_bot = mock.MagicMock(did="did")
    monkeypatch.setattr(server_module.bot_repo, "get", lambda _did: fake_bot)
    monkeypatch.setattr(server_module.bot_repo, "set_mqtt", mock.MagicMock())

    plugin._set_client_connected("did@botclass/res", True, Session())

    server_module.bot_repo.set_mqtt.assert_called_once()
