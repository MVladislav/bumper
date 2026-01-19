"""Init module."""

import argparse
import asyncio
from contextlib import suppress
import logging
from pathlib import Path
import sys

from bumper.db import bot_repo, client_repo, token_repo
from bumper.mqtt import helper_bot, server as server_mqtt
from bumper.utils import utils
from bumper.utils.certs import generate_certificates
from bumper.utils.log_helper import LogHelper
from bumper.utils.settings import config as bumper_isc
from bumper.web import server as server_web
from bumper.xmpp import xmpp as server_xmpp

LogHelper()

_LOGGER = logging.getLogger(__name__)


async def start() -> None:
    """Start Bumper."""
    try:
        _LOGGER.info("Starting Bumpers...")
        await start_configuration()
        await start_service()
        _LOGGER.info("Bumper started successfully")
        await maintenance()
    except Exception:
        _LOGGER.exception("Failed to start Bumper")


async def start_configuration() -> None:
    """Initialize Bumper configuration."""
    if bumper_isc.debug_bumper_level == "DEBUG":
        asyncio.get_running_loop().set_debug(True)

    if not bumper_isc.bumper_listen:
        error_message = "No listen address configured!"
        _LOGGER.error(error_message)
        raise ValueError(error_message)

    bot_repo.reset_all_connections()
    client_repo.reset_all_connections()

    if bumper_isc.BUMPER_PROXY_MQTT is True:
        _LOGGER.info("Proxy MQTT Enabled")
    if bumper_isc.BUMPER_PROXY_WEB is True:
        _LOGGER.info("Proxy Web Enabled")

    bumper_isc.mqtt_server = server_mqtt.MQTTServer(
        [
            server_mqtt.MQTTBinding(bumper_isc.bumper_listen, bumper_isc.MQTT_LISTEN_PORT_TLS, True),
            server_mqtt.MQTTBinding(bumper_isc.bumper_listen, bumper_isc.MQTT_LISTEN_PORT, False),
        ],
    )
    # bumper_isc.mqtt_helperbot = helper_bot.MQTTHelperBot(bumper_isc.bumper_listen, bumper_isc.MQTT_LISTEN_PORT_TLS, True)
    bumper_isc.mqtt_helperbot = helper_bot.MQTTHelperBot(bumper_isc.bumper_listen, bumper_isc.MQTT_LISTEN_PORT, False)
    bumper_isc.web_server = server_web.WebServer(
        [
            server_web.WebserverBinding(bumper_isc.bumper_listen, int(bumper_isc.WEB_SERVER_TLS_LISTEN_PORT), True),
            server_web.WebserverBinding(bumper_isc.bumper_listen, int(bumper_isc.WEB_SERVER_LISTEN_PORT), False),
        ],
        proxy_mode=bumper_isc.BUMPER_PROXY_WEB,
    )
    bumper_isc.xmpp_server = server_xmpp.XMPPServer(bumper_isc.bumper_listen, bumper_isc.XMPP_LISTEN_PORT_TLS)


async def start_service() -> None:
    """Start Bumper services."""
    # Start XMPP Server
    if bumper_isc.xmpp_server is not None:
        utils.store_service(bumper_isc.xmpp_server.start_async_server())

    # Start MQTT Server
    if bumper_isc.mqtt_server is not None:
        await bumper_isc.mqtt_server.start()
        while bumper_isc.mqtt_server.state != "started":
            _LOGGER.info("Waiting for MQTT server to start...")
            await asyncio.sleep(0.1)

        # Start MQTT Helperbot
        if bumper_isc.mqtt_helperbot is not None:
            await bumper_isc.mqtt_helperbot.start()
            while not await bumper_isc.mqtt_helperbot.is_connected:
                _LOGGER.info("Waiting for HelperBot to connect...")
                await asyncio.sleep(0.1)

    # Start web servers
    if bumper_isc.web_server is not None:
        utils.store_service(bumper_isc.web_server.start())


async def maintenance() -> None:
    """Run periodic maintenance tasks."""
    try:
        while not bumper_isc.shutting_down:
            token_repo.revoke_expired()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass


async def shutdown() -> None:
    """Shutdown Bumper."""
    _LOGGER.info("Shutting down...")
    bumper_isc.shutting_down = True

    if bumper_isc.mqtt_helperbot is not None:
        await bumper_isc.mqtt_helperbot.disconnect()

    if bumper_isc.web_server is not None:
        await bumper_isc.web_server.shutdown()

    if bumper_isc.mqtt_server is not None:
        while bumper_isc.mqtt_server.state in ["starting", "stopping"]:
            _LOGGER.info("Waiting for MQTT Server to stabilize before shutdown...")
            await asyncio.sleep(0.1)
        if bumper_isc.mqtt_server.state == "started":
            await bumper_isc.mqtt_server.shutdown()

    if bumper_isc.xmpp_server is not None and bumper_isc.xmpp_server.server:
        await bumper_isc.xmpp_server.disconnect()

    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    # tasks = [task for task in bumper_isc.background_tasks if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    with suppress(asyncio.CancelledError):
        await asyncio.gather(*tasks)

    _LOGGER.info("Shutdown complete!")


def read_args(argv: list[str] | None) -> None:
    """Parse command-line arguments."""
    argv = argv or sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=str, help="Start serving on address")
    parser.add_argument("--announce", type=str, help="Announce address to bots on check-in")
    parser.add_argument("--debug_level", type=str, help="Enable debug logs")
    parser.add_argument("--debug_verbose", type=int, help="Enable verbose debug logs")
    args = parser.parse_args(argv)

    if args.debug_level:
        bumper_isc.debug_bumper_level = args.debug_level  # debug_bumper_level
    if args.debug_verbose:
        bumper_isc.debug_bumper_verbose = args.debug_verbose  # debug_bumper_verbose
    if args.listen:
        bumper_isc.bumper_listen = args.listen
    if args.announce:
        bumper_isc.bumper_announce_ip = args.announce

    LogHelper()


async def _lifecycle(argv: list[str] | None = None) -> None:
    """Run main lifecycle."""
    try:
        passwd_path = Path(bumper_isc.data_dir) / "passwd"
        passwd_path.touch(exist_ok=True)

        read_args(argv)

        if not utils.is_valid_ip(bumper_isc.bumper_listen):
            error_message = "Invalid listen address configured!"
            raise ValueError(error_message)

        # Generate certificates if they don't exist
        generate_certificates(
            bumper_isc.certs_dir,
            bumper_isc.ca_cert,
            bumper_isc.server_cert,
            bumper_isc.server_key,
        )

        await start()  # 👉 enters maintenance() and spins until shutdown flag
    except KeyboardInterrupt:
        _LOGGER.debug("Keyboard Interrupt!")
    except Exception:
        _LOGGER.critical(utils.default_exception_str_builder())
    finally:
        await shutdown()


def main(argv: list[str] | None = None) -> None:
    """Start the main entry point for Bumper."""
    try:
        asyncio.run(_lifecycle(argv))
    except Exception:
        _LOGGER.critical(utils.default_exception_str_builder())
