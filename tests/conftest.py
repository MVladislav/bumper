"""Pytest fixtures for bumper integration and unit tests.

This module sets up test files, configures logging, and provides fixtures for
MQTT, XMPP, and web server components used in bumper tests.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Generator
import logging
from pathlib import Path
import ssl
import tracemalloc

from aiohttp.test_utils import TestClient
from aiohttp.web import Application
from aiomqtt import Client
import pytest

from bumper.db import db
from bumper.mqtt.helper_bot import MQTTHelperBot
from bumper.mqtt.server import MQTTBinding, MQTTServer
from bumper.utils.certs import generate_certificates
from bumper.utils.log_helper import LogHelper
from bumper.utils.settings import config as bumper_isc
from bumper.web.server import WebServer, WebserverBinding
from bumper.xmpp.xmpp import XMPPServer
from tests import HOST, MQTT_PORT, WEBSERVER_PORT


@pytest.fixture(scope="session", autouse=True)
def enable_tracemalloc() -> Generator[None]:
    """Enable tracemalloc to detect memory leaks."""
    tracemalloc.start()
    yield
    tracemalloc.stop()


@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> Generator[None]:
    """Configure root logger for test session."""
    logging.basicConfig(level=logging.DEBUG, force=True)
    logger = logging.getLogger()
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    yield
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)


@pytest.fixture(scope="session")
def test_files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Create test files and override config paths."""
    tmp_dir = tmp_path_factory.mktemp("test_files")
    passwd_file = tmp_dir / "passwd"
    passwd_file.write_text(
        "test-client:$6$e9026a738b07b5a1$WaoYMI61aIPhhjfe3FG3uzV1oqyRdLi/TvLbBbvvzFyJ7T6PrileHGkzKkJUMLGQm/dhcq0fUT8mcu2kVcjbX/\n",
    )
    passwd_bad = tmp_dir / "passwd_bad"
    passwd_bad.write_text("test-client:badhash\n")

    certs_dir = tmp_dir / "certs"
    ca_cert_path = certs_dir / "ca.crt"
    server_cert_path = certs_dir / "bumper.crt"
    server_key_path = certs_dir / "bumper.key"
    generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

    db_file = tmp_dir / "tmp.db"

    bumper_isc.ca_cert = certs_dir / "ca.crt"
    bumper_isc.server_cert = certs_dir / "bumper.crt"
    bumper_isc.server_key = certs_dir / "bumper.key"
    bumper_isc.db_file = str(db_file)

    return {
        "passwd": passwd_file,
        "passwd_bad": passwd_bad,
        "certs": certs_dir,
        "db": db_file,
    }


@pytest.fixture
def clean_database(test_files: dict[str, Path]) -> None:
    """Clean and reset test database between tests."""
    db.get_db().drop_tables()
    db_file = test_files["db"]
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def log_helper(level: str) -> LogHelper:
    """Create LogHelper with specified level."""
    bumper_isc.debug_bumper_level = level
    bumper_isc.debug_bumper_verbose = 2
    return LogHelper()


@pytest.fixture
async def mqtt_server(test_files: dict[str, Path]) -> AsyncIterator[MQTTServer]:
    """Start authenticated MQTT server."""
    bumper_isc.mqtt_server = await _start_mqtt_server(str(test_files["passwd"]))
    yield bumper_isc.mqtt_server
    await bumper_isc.mqtt_server.shutdown()


@pytest.fixture
async def mqtt_server_anonymous(test_files: dict[str, Path]) -> AsyncIterator[MQTTServer]:
    """Start anonymous MQTT server."""
    bumper_isc.mqtt_server = await _start_mqtt_server(str(test_files["passwd"]), allow_anonymous=True)
    yield bumper_isc.mqtt_server
    await bumper_isc.mqtt_server.shutdown()


async def _start_mqtt_server(password_file: str, allow_anonymous: bool = False) -> MQTTServer:
    """Start MQTT server helper."""
    server = MQTTServer(
        MQTTBinding(HOST, MQTT_PORT, use_ssl=True),
        password_file=password_file,
        allow_anonymous=allow_anonymous,
    )
    await server.start()
    started_event = asyncio.Event()

    def on_state_change() -> None:
        if server.state == "started":
            started_event.set()

    server.on_state_change = on_state_change
    if server.state != "started":
        await started_event.wait()
    return server


@pytest.fixture
async def mqtt_client(mqtt_server: MQTTServer) -> AsyncIterator[Client]:
    """Create MQTT client with TLS."""
    if mqtt_server.state != "started":
        msg = "MQTT server must be started before creating client."
        raise RuntimeError(msg)

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="helperbot@bumper/test",
    ) as client:
        yield client


@pytest.fixture
async def helper_bot(mqtt_server: MQTTServer) -> AsyncIterator[MQTTHelperBot]:
    """Start MQTTHelperBot connected to test broker."""
    if mqtt_server.state != "started":
        msg = "MQTT server must be started before creating client."
        raise RuntimeError(msg)

    bumper_isc.mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True, 0.1)
    await bumper_isc.mqtt_helperbot.start()

    if await bumper_isc.mqtt_helperbot.is_connected is not True:
        msg = "MQTT helper bot should be connected with MQTT server."
        raise RuntimeError(msg)

    yield bumper_isc.mqtt_helperbot
    await bumper_isc.mqtt_helperbot.disconnect()


@pytest.fixture
async def xmpp_server() -> AsyncIterator[XMPPServer]:
    """Start XMPP server."""
    bumper_isc.xmpp_server = XMPPServer(HOST, 5223)
    await bumper_isc.xmpp_server.start_async_server()
    yield bumper_isc.xmpp_server
    await bumper_isc.xmpp_server.disconnect()


@pytest.fixture
def xmpp_cleanup_clients() -> Generator[None]:
    """Ensure all XMPPAsyncClient instances are cleaned up after each test."""
    yield
    for client in XMPPServer.clients:
        client.cleanup()
    XMPPServer.clients.clear()


@pytest.fixture
async def webserver_client(
    aiohttp_client: Callable[[Application], Awaitable[TestClient]],
    mqtt_server: MQTTServer,
) -> AsyncIterator[TestClient]:
    """Start web server and create aiohttp client."""
    if mqtt_server.state != "started":
        msg = "MQTT server must be started before creating client."
        raise RuntimeError(msg)

    bumper_isc.web_server = WebServer(
        WebserverBinding(HOST, WEBSERVER_PORT, False),
        False,
    )
    client = await aiohttp_client(bumper_isc.web_server._app)
    yield client
    await client.close()
