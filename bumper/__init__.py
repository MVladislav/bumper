"""Init module."""

import argparse
import asyncio
import contextlib
import logging
from pathlib import Path
import sys

from bumper.db import bot_repo, client_repo, identity, token_repo, user_repo
from bumper.db.migration import migrate_db
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
    bumper_isc.shutting_down = False
    bumper_isc.shutdown_event = asyncio.Event()
    if bumper_isc.debug_bumper_level == "DEBUG":
        asyncio.get_running_loop().set_debug(True)

    if not bumper_isc.bumper_listen:
        error_message = "No listen address configured!"
        _LOGGER.error(error_message)
        raise ValueError(error_message)

    generate_certificates()

    migrate_db()

    identity.reconcile_users()
    identity.reconcile_bot_owners()
    bot_repo.reset_all_connections()
    client_repo.reset_all_connections()
    client_repo.reconcile(user_repo.list_all())

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
    bumper_isc.mqtt_helperbot = helper_bot.MQTTHelperBot(
        bumper_isc.bumper_listen,
        bumper_isc.MQTT_LISTEN_PORT,
        False,
        bumper_isc.HELPER_BOT_TIMEOUT,
    )
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
        await bumper_isc.xmpp_server.start_async_server()

    # Start MQTT Server
    if bumper_isc.mqtt_server is not None:
        await bumper_isc.mqtt_server.start()
        if bumper_isc.mqtt_server.state != "started":
            msg = f"MQTT server did not start; current state is {bumper_isc.mqtt_server.state}"
            raise RuntimeError(msg)

        # Start MQTT Helperbot
        if bumper_isc.mqtt_helperbot is not None:
            await bumper_isc.mqtt_helperbot.start()
            while not await bumper_isc.mqtt_helperbot.is_connected:
                _LOGGER.info("Waiting for HelperBot to connect...")
                await asyncio.sleep(0.1)

    # Start web servers
    if bumper_isc.web_server is not None:
        await bumper_isc.web_server.start()


async def maintenance() -> None:
    """Run periodic maintenance tasks."""
    try:
        while not bumper_isc.shutting_down:
            token_repo.revoke_expired()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(bumper_isc.shutdown_event.wait(), timeout=5)
    except asyncio.CancelledError:
        pass


async def shutdown() -> None:
    """Shutdown Bumper."""
    _LOGGER.info("Shutting down...")
    bumper_isc.shutting_down = True
    bumper_isc.shutdown_event.set()

    if bumper_isc.mqtt_helperbot is not None:
        await bumper_isc.mqtt_helperbot.disconnect()
        bumper_isc.mqtt_helperbot = None

    if bumper_isc.web_server is not None:
        await bumper_isc.web_server.shutdown()
        bumper_isc.web_server = None

    if bumper_isc.mqtt_server is not None:
        mqtt_server = bumper_isc.mqtt_server
        if mqtt_server.state in {"starting", "stopping"}:
            await mqtt_server.wait_for_state_change(
                mqtt_server.state,
                reverse=True,
                max_wait=server_mqtt.SHUTDOWN_TIMEOUT,
            )
        if mqtt_server.state == "started":
            await mqtt_server.shutdown()
        elif mqtt_server.state not in {"stopped", "not_started"}:
            _LOGGER.warning(f"MQTT server did not reach a stopped state :: state={mqtt_server.state}")
        bumper_isc.mqtt_server = None

    if bumper_isc.xmpp_server is not None:
        await bumper_isc.xmpp_server.disconnect()
        bumper_isc.xmpp_server = None

    tasks = [task for task in bumper_isc.background_tasks if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

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
