"""Web paths for bumper web server."""

from collections.abc import Awaitable, Callable
from datetime import datetime
from importlib.resources import files
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2

from bumper.db import bot_repo, clean_log_repo, client_repo, user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc

if TYPE_CHECKING:
    from bumper.web.models import BumperUser, CleanLog, VacBotClient, VacBotDevice

_LOGGER = logging.getLogger(__name__)
_LOGGER_PROXY = logging.getLogger(f"{__name__}.proxy")


# ******************************************************************************


async def handle_favicon(_: Request) -> web.FileResponse:
    """Serve the favicon.ico file."""
    try:
        favicon_path = Path(str(files("bumper.web").joinpath("static_web/favicon.ico")))
        if not await utils.check_file_exists(favicon_path):
            msg = f"Favicon not found at {favicon_path}"
            raise FileNotFoundError(msg)
        return web.FileResponse(path=favicon_path)
    except Exception as e:
        _LOGGER.exception("Failed to serve favicon.ico")
        raise HTTPInternalServerError from e


# ******************************************************************************


async def handle_restart_service(request: Request) -> Response:
    """Handle restart services."""
    try:
        service = request.match_info.get("service", "")
        if service == "Helperbot":
            if await _restart_helper_bot():
                return web.json_response({"status": "complete"})
            return web.json_response({"status": "failed"})
        if service == "MQTTServer":
            if await _restart_mqtt_server():
                return web.json_response({"status": "complete"})
            return web.json_response({"status": "failed"})
        if service == "XMPPServer" and bumper_isc.xmpp_server is not None:
            await bumper_isc.xmpp_server.disconnect()
            await bumper_isc.xmpp_server.start_async_server()
            return web.json_response({"status": "complete"})
        return web.json_response({"status": "invalid service"})
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def _restart_helper_bot() -> bool:
    """Restart helper bot."""
    if bumper_isc.mqtt_helperbot is not None:
        await bumper_isc.mqtt_helperbot.disconnect()
        await bumper_isc.mqtt_helperbot.start()
        return True
    return False


async def _restart_mqtt_server() -> bool:
    """Restart mqtt server."""
    if bumper_isc.mqtt_server is not None:
        _LOGGER.info("Restarting MQTT Server...")
        await bumper_isc.mqtt_server.shutdown()
        await bumper_isc.mqtt_server.wait_for_state_change("stopped")
        if bumper_isc.mqtt_server.state != "stopped":
            _LOGGER.warning("MQTT Server failed to stop")
            return False
        await bumper_isc.mqtt_server.start()
        await bumper_isc.mqtt_server.wait_for_state_change("started")
        if bumper_isc.mqtt_server.state == "started":
            _LOGGER.info("MQTT Server restarted successfully")
            return True
    _LOGGER.warning("MQTT Server failed to restart")
    return False


# ******************************************************************************


async def handle_base(request: Request) -> Response:
    """Handle the base route."""
    try:
        context = {
            **await _get_context(request),
            **await _get_context(request, "server_status"),
            **await _get_context(request, "bots"),
            **await _get_context(request, "clients"),
            **await _get_context(request, "users"),
            **await _get_context(request, "clean_logs"),
        }
        return aiohttp_jinja2.render_template("home.jinja2", request, context=context)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


def handle_partial(template_name: str) -> Callable[[Request], Awaitable[Response]]:
    """Handle partials."""

    async def handler(request: Request) -> Response:
        try:
            context = await _get_context(request, template_name)
            return aiohttp_jinja2.render_template(f"partials/{template_name}.jinja2", request, context)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    return handler


async def _get_context(request: Request, template_name: str | None = None) -> dict[str, Any]:
    if template_name and template_name == "server_status":
        return {
            "mqtt_server": {
                "state": bumper_isc.mqtt_server.state if bumper_isc.mqtt_server else "offline",
                "sessions": {
                    "clients": [
                        {
                            "username": session.username,
                            "client_id": session.client_id,
                            "state": session.transitions.state,
                        }
                        for session in bumper_isc.mqtt_server.sessions
                    ]
                    if bumper_isc.mqtt_server
                    else [],
                },
            },
            "xmpp_server": {
                "state": (
                    ("running" if bumper_isc.xmpp_server.server and bumper_isc.xmpp_server.server.is_serving() else "stopped")
                    if bumper_isc.xmpp_server
                    else "offline"
                ),
                "sessions": {
                    "clients": [client.to_dict() for client in bumper_isc.xmpp_server.clients] if bumper_isc.xmpp_server else [],
                },
            },
            "helperbot": {
                "state": await utils.with_timeout(bumper_isc.mqtt_helperbot.is_connected)
                if bumper_isc.mqtt_helperbot
                else "offline",
            },
        }
    if template_name and template_name == "bots":
        return {
            "bots": [
                {
                    "name": bot.name,
                    "nick": bot.nick,
                    "did": bot.did,
                    "class_id": bot.class_id,
                    "resource": bot.resource,
                    "company": bot.company,
                    "mqtt_connection": bot.mqtt_connection,
                    "xmpp_connection": bot.xmpp_connection,
                }
                for bot in bot_repo.list_all()
            ],
        }
    if template_name and template_name == "clients":
        return {
            "clients": [
                {
                    "name": client.name,
                    "userid": client.userid,
                    "realm": client.realm,
                    "resource": client.resource,
                    "mqtt_connection": client.mqtt_connection,
                    "xmpp_connection": client.xmpp_connection,
                }
                for client in client_repo.list_all()
            ],
        }
    if template_name and template_name == "users":
        return {
            "users": [
                {
                    "username": user.username,
                    "userid": user.userid,
                    "devices": user.devices,
                }
                for user in user_repo.list_all()
            ],
        }
    if template_name and template_name == "clean_logs":
        offset = int(request.query.get("offset", 0))
        limit = int(request.query.get("limit", 5))
        clean_log_repo_list = sorted(clean_log_repo.list_all(), key=lambda x: (x.ts, x.did), reverse=True)
        clean_log_repo_list_count = len(clean_log_repo_list)
        clean_log_repo_list_limit = clean_log_repo_list[offset : offset + limit]
        return {
            "count": clean_log_repo_list_count,
            "clean_logs": [
                {
                    "clean_log_id": clean_log.clean_log_id,
                    "did": clean_log.did,
                    "cid": clean_log.cid,
                    # "aiavoid": clean_log.aiavoid,
                    # "aitypes": clean_log.aitypes,
                    "area": clean_log.area or 0,
                    # "image_url": clean_log.image_url,
                    "stop_reason": clean_log.stop_reason,
                    "last": clean_log.last or 0,
                    "ts": datetime.fromtimestamp(clean_log.ts, tz=bumper_isc.LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M")  # :%S
                    if clean_log.ts
                    else None,
                    "type": clean_log.type,
                    # "avoid_count": clean_log.avoid_count,
                    # "enable_power_mop": clean_log.enable_power_mop,
                    # "power_mop_type": clean_log.power_mop_type,
                    # "ai_open": clean_log.ai_open,
                }
                for clean_log in clean_log_repo_list_limit
            ],
            "offset": offset,
            "limit": limit,
            "has_next": offset + limit < clean_log_repo_list_count,
            "has_prev": offset > 0,
        }
    return {
        "app_version": bumper_isc.APP_VERSION,
        "github_repo": bumper_isc.GITHUB_REPO,
        "github_release": bumper_isc.GITHUB_RELEASE,
    }


def handle_remove_entity(entity_type: str) -> Callable[[Request], Awaitable[Response]]:
    """Handle remove entity."""

    async def handler(request: Request) -> Response:
        try:
            remove_func: Callable[..., None] | None = None
            get_func: Callable[..., VacBotClient | VacBotDevice | BumperUser | CleanLog | list[CleanLog] | None] | None = None
            entity_id: str | None = None
            if entity_type == "bot":
                entity_id = request.match_info.get("did")
                remove_func = bot_repo.remove
                get_func = bot_repo.get
            elif entity_type == "client":
                entity_id = request.match_info.get("userid")
                remove_func = client_repo.remove
                get_func = client_repo.get
            elif entity_type == "user":
                entity_id = request.match_info.get("userid")
                remove_func = user_repo.remove
                get_func = user_repo.get_by_id
            elif entity_type == "clean_log":
                entity_id = request.match_info.get("clean_log_id")
                remove_func = clean_log_repo.remove_by_id
                get_func = clean_log_repo.list_by_id
            elif entity_type == "clean_logs":
                remove_func = clean_log_repo.clear
                get_func = clean_log_repo.list_all

            if not entity_id and remove_func and get_func:
                remove_func()
                if (list_res := get_func()) and isinstance(list_res, list) and len(list_res) > 0:
                    return web.json_response({"status": f"failed to remove {entity_type}"})
                return web.json_response({"status": f"successfully removed {entity_type}"})
            if entity_id and remove_func and get_func:
                remove_func(entity_id)
                if get_func(entity_id):
                    return web.json_response({"status": f"failed to remove {entity_type}"})
                return web.json_response({"status": f"successfully removed {entity_type}"})
            return web.json_response({"status": f"not implemented for {entity_type}"})
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    return handler
