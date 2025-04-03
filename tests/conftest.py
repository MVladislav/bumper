import asyncio
import os
import ssl

from aiomqtt import Client
import pytest

from bumper.mqtt.helper_bot import MQTTHelperBot
from bumper.mqtt.server import MQTTBinding, MQTTServer
from bumper.utils import db
from bumper.utils.log_helper import LogHelper
from bumper.utils.settings import config as bumper_isc
from bumper.web.server import WebServer, WebserverBinding
from tests import HOST, MQTT_PORT, WEBSERVER_PORT


# NOTE: use with:
# @pytest.mark.usefixtures("clean_database")
@pytest.fixture(name="clean_database")
def _clean_database() -> None:
    db._db_get().drop_tables()
    if os.path.exists("tests/_test_files/tmp.db"):
        os.remove("tests/_test_files/tmp.db")  # Remove existing db


# NOTE: use with:
# @pytest.mark.parametrize("level", ["DEBUG"])
# @pytest.mark.usefixtures("log_helper")
@pytest.fixture
def log_helper(level: str):
    bumper_isc.bumper_level = level
    bumper_isc.bumper_verbose = 2
    return LogHelper()


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for the test session."""
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.handlers.clear()

    # Use a stream handler to avoid closed file errors
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)

    yield

    # Ensure all handlers are properly closed
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)


@pytest.fixture
async def mqtt_server():
    """Fixture to start and stop the MQTT server."""
    bumper_isc.mqtt_server = MQTTServer(MQTTBinding(HOST, MQTT_PORT, True), password_file="tests/_test_files/passwd")

    await bumper_isc.mqtt_server.start()
    while bumper_isc.mqtt_server.state != "started":
        await asyncio.sleep(0.1)

    yield bumper_isc.mqtt_server

    await bumper_isc.mqtt_server.shutdown()


@pytest.fixture
async def mqtt_client(mqtt_server: MQTTServer):
    """Fixture to create and connect an MQTT client."""
    assert mqtt_server.state == "started"

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with Client(
        hostname=HOST,
        port=MQTT_PORT,
        tls_context=ssl_ctx,
        identifier="helperbot@bumper/test",  # Client identifier
    ) as client:
        yield client


@pytest.fixture
async def helper_bot(mqtt_server: MQTTServer):
    """Fixture to start and stop the helper bot."""
    assert mqtt_server.state == "started"

    bumper_isc.mqtt_helperbot = MQTTHelperBot(HOST, MQTT_PORT, True, 0.1)
    await bumper_isc.mqtt_helperbot.start()
    assert await bumper_isc.mqtt_helperbot.is_connected

    yield bumper_isc.mqtt_helperbot

    await bumper_isc.mqtt_helperbot.disconnect()


@pytest.fixture
async def webserver_client(aiohttp_client):
    """Fixture to create a web server client."""
    bumper_isc.web_server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, False), False)
    client = await aiohttp_client(bumper_isc.web_server._app)

    yield client

    await client.close()


@pytest.fixture
def create_webserver():
    """Fixture to create a web server instance."""
    return WebServer(WebserverBinding(HOST, WEBSERVER_PORT, False), False)
