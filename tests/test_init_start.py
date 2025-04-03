import asyncio
import os

import pytest
from testfixtures import LogCapture

import bumper
from bumper.utils.settings import config as bumper_isc


@pytest.mark.parametrize(("debug", "proxy"), [(False, False), (True, False), (False, True), (True, True)])
async def test_start_stop(debug: bool, proxy: bool) -> None:
    with LogCapture() as log:
        if proxy:
            bumper_isc.BUMPER_PROXY_MQTT = True
            bumper_isc.BUMPER_PROXY_WEB = True
        bumper_isc.bumper_verbose = 2
        if debug:
            bumper_isc.bumper_level = "DEBUG"

        if os.path.exists("tests/_test_files/tmp.db"):
            os.remove("tests/_test_files/tmp.db")  # Remove existing db

        asyncio.Task(bumper.start())
        await asyncio.sleep(0.1)

        log.check_present(("bumper", "INFO", "Starting Bumpers..."))

        while True:
            try:
                log.check_present(("bumper", "INFO", "Bumper started successfully"))
                break
            except AssertionError:
                pass
            await asyncio.sleep(0.1)

        if proxy:
            assert bumper_isc.BUMPER_PROXY_MQTT is True
            log.check_present(("bumper", "INFO", "Proxy MQTT Enabled"))
            assert bumper_isc.BUMPER_PROXY_WEB is True
            log.check_present(("bumper", "INFO", "Proxy Web Enabled"))

        assert bumper_isc.bumper_listen is not None

        assert bumper_isc.xmpp_server is not None
        assert bumper_isc.mqtt_server is not None
        assert bumper_isc.mqtt_server.state == "started"
        assert bumper_isc.mqtt_helperbot is not None
        assert await bumper_isc.mqtt_helperbot.is_connected is True
        assert bumper_isc.web_server is not None

        log.clear()

        await asyncio.Task(bumper.shutdown())
        log.check_present(("bumper", "INFO", "Shutting down..."), ("bumper", "INFO", "Shutdown complete!"))
        assert bumper_isc.shutting_down is True

    if proxy:
        bumper_isc.BUMPER_PROXY_MQTT = False
        bumper_isc.BUMPER_PROXY_WEB = False


async def test_start_missing_listen() -> None:
    with LogCapture() as log:
        bumper_isc.bumper_verbose = 2
        bumper_isc.bumper_listen = None

        if os.path.exists("tests/_test_files/tmp.db"):
            os.remove("tests/_test_files/tmp.db")  # Remove existing db

        asyncio.Task(bumper.start())
        await asyncio.sleep(0.2)

        assert bumper_isc.bumper_listen is None

        log.check_present(
            ("bumper", "INFO", "Starting Bumpers..."),
            ("bumper", "ERROR", "No listen address configured!"),
        )
