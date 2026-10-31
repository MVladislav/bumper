"""Integration tests for bumper.start() and bumper.shutdown().

Also verifies the __main__ entrypoint runs without side effects.
"""

import asyncio
import runpy
import socket
import sys
from unittest import mock

import pytest
from testfixtures import LogCapture

import bumper
import bumper.__main__
from bumper.utils.settings import config as bumper_isc


def _available_port(used: set[int]) -> int:
    """Choose an unused high port for a full-stack lifecycle test."""
    while True:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        if port not in used:
            used.add(port)
            return port


async def _wait_for_services(start_task: asyncio.Task[None]) -> bool:
    """Wait until startup has brought each configured service online."""
    for _ in range(500):
        if start_task.done():
            return False
        mqtt_server = bumper_isc.mqtt_server
        helper_bot = bumper_isc.mqtt_helperbot
        xmpp_server = bumper_isc.xmpp_server
        web_server = bumper_isc.web_server
        if (
            mqtt_server is not None
            and mqtt_server.state == "started"
            and helper_bot is not None
            and helper_bot._is_connected
            and xmpp_server is not None
            and xmpp_server.server is not None
            and xmpp_server.server.is_serving()
            and web_server is not None
            and web_server.started
        ):
            await asyncio.sleep(0)
            return not start_task.done()
        await asyncio.sleep(0.01)
    return False


@pytest.mark.parametrize(
    ("debug", "proxy"),
    [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ],
)
@pytest.mark.usefixtures("clean_database")
async def test_start_stop(debug: bool, proxy: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """Start and stop bumper with combinations of debug and proxy settings."""
    # Configure settings
    bumper_isc.debug_bumper_verbose = 2
    if debug:
        bumper_isc.debug_bumper_level = "DEBUG"
    bumper_isc.BUMPER_PROXY_MQTT = proxy
    bumper_isc.BUMPER_PROXY_WEB = proxy
    monkeypatch.setattr(bumper_isc, "bumper_listen", "127.0.0.1")
    used_ports: set[int] = set()
    for setting in (
        "XMPP_LISTEN_PORT_TLS",
        "MQTT_LISTEN_PORT_TLS",
        "MQTT_LISTEN_PORT",
        "WEB_SERVER_TLS_LISTEN_PORT",
        "WEB_SERVER_LISTEN_PORT",
    ):
        monkeypatch.setattr(bumper_isc, setting, _available_port(used_ports))

    with LogCapture() as log:
        # Startup remains alive in maintenance until shutdown is requested.
        start_task = asyncio.create_task(bumper.start())
        assert await asyncio.wait_for(_wait_for_services(start_task), timeout=5)
        log.check_present(("bumper", "INFO", "Starting Bumpers..."))
        log.check_present(("bumper", "INFO", "Bumper started successfully"))

        if proxy:
            assert bumper_isc.BUMPER_PROXY_MQTT is True
            log.check_present(("bumper", "INFO", "Proxy MQTT Enabled"))
            assert bumper_isc.BUMPER_PROXY_WEB is True
            log.check_present(("bumper", "INFO", "Proxy Web Enabled"))

        # Verify services are running
        assert bumper_isc.bumper_listen is not None
        assert bumper_isc.xmpp_server is not None
        assert bumper_isc.mqtt_server.state == "started"
        assert await bumper_isc.mqtt_helperbot.is_connected is True
        assert bumper_isc.web_server is not None

        log.clear()

        # Shutdown and await completion
        await bumper.shutdown()
        await asyncio.wait_for(start_task, timeout=2)

        log.check_present(
            ("bumper", "INFO", "Shutting down..."),
            ("bumper", "INFO", "Shutdown complete!"),
        )
        assert bumper_isc.shutting_down is True

    # Reset proxy flags
    bumper_isc.BUMPER_PROXY_MQTT = False
    bumper_isc.BUMPER_PROXY_WEB = False


@pytest.mark.usefixtures("clean_database")
async def test_start_missing_listen() -> None:
    """Starting bumper without listen address logs an error and stops."""
    bumper_isc.debug_bumper_verbose = 2
    bumper_isc.bumper_listen = None

    with LogCapture() as log:
        # run start and allow error
        task = asyncio.create_task(bumper.start())
        await asyncio.wait_for(task, timeout=1)

        log.check_present(
            ("bumper", "INFO", "Starting Bumpers..."),
            ("bumper", "ERROR", "No listen address configured!"),
        )

        assert bumper_isc.bumper_listen is None


@mock.patch("bumper.start")
@mock.patch("bumper.shutdown")
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_main_entrypoint(mock_shutdown: mock.MagicMock, mock_start: mock.MagicMock) -> None:
    """Running bumper via __main__ entry point triggers shutdown but not start."""
    with LogCapture():
        with mock.patch.object(sys, "argv", []):
            runpy.run_module("bumper", run_name="__main__")

        mock_start.assert_not_called()
        mock_shutdown.assert_called_once()
