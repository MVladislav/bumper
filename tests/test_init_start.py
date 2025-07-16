"""Integration tests for bumper.start() and bumper.shutdown().

Also verifies the __main__ entrypoint runs without side effects.
"""

import asyncio
import runpy
import sys
from unittest import mock

import pytest
from testfixtures import LogCapture

import bumper
from bumper.utils.settings import config as bumper_isc


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
async def test_start_stop(debug: bool, proxy: bool) -> None:
    """Start and stop bumper with combinations of debug and proxy settings."""
    # Configure settings
    bumper_isc.debug_bumper_verbose = 2
    if debug:
        bumper_isc.debug_bumper_level = "DEBUG"
    bumper_isc.BUMPER_PROXY_MQTT = proxy
    bumper_isc.BUMPER_PROXY_WEB = proxy

    with LogCapture() as log:
        # Launch start() in background
        start_task = asyncio.create_task(bumper.start())
        await asyncio.wait_for(start_task, timeout=1)
        log.check_present(("bumper", "INFO", "Starting Bumpers..."))

        # Await startup log, timeout after 5s
        await asyncio.wait_for(
            asyncio.to_thread(lambda: log.check_present(("bumper", "INFO", "Bumper started successfully"))),
            timeout=5,
        )

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
def test_main_entrypoint(mock_shutdown: mock.MagicMock, mock_start: mock.MagicMock) -> None:
    """Running bumper via __main__ entry point triggers shutdown but not start."""
    with LogCapture():
        with mock.patch.object(sys, "argv", []):
            runpy.run_module("bumper", run_name="__main__")

        mock_start.assert_not_called()
        mock_shutdown.assert_called_once()
