"""Web server module."""

import asyncio
from collections.abc import Awaitable, Callable
import dataclasses
from importlib.resources import files
import logging
from pathlib import Path
import ssl
from typing import TYPE_CHECKING, Any

from aiohttp import ClientSession, TCPConnector, web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
import jinja2
from yarl import URL

from bumper.db import bot_repo, client_repo, user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import middlewares, plugins, single_paths

if TYPE_CHECKING:
    from bumper.web.models import BumperUser, VacBotClient, VacBotDevice

_LOGGER = logging.getLogger(__name__)
_LOGGER_PROXY = logging.getLogger(f"{__name__}.proxy")


@dataclasses.dataclass(frozen=True)
class WebserverBinding:
    """Webserver binding."""

    host: str
    port: int
    use_ssl: bool


class WebServer:
    """Web server."""

    def __init__(self, bindings: list[WebserverBinding] | WebserverBinding, proxy_mode: bool) -> None:
        """Web Server init."""
        self._runners: list[web.AppRunner] = []
        self._bindings = [bindings] if isinstance(bindings, WebserverBinding) else bindings
        self._app = web.Application(middlewares=[middlewares.log_all_requests])

        templates_path = self._resolve_path("templates")
        static_path = self._resolve_path("static")

        aiohttp_jinja2.setup(
            self._app,
            loader=jinja2.FileSystemLoader(str(templates_path)),
            auto_reload=False,  # Prevent constant template reloading
            cache_size=800,  # Increase cache size for frequent templates
            autoescape=True,
        )
        self._add_routes(proxy_mode, static_path)
        self._app.freeze()  # no modification allowed anymore

    def _resolve_path(self, folder: str) -> Path:
        """Resolve the path for templates or static files."""
        path = Path(bumper_isc.bumper_dir) / "bumper" / "web" / folder
        return path if path.exists() else Path(str(files("bumper.web").joinpath(folder)))

    def _add_routes(self, proxy_mode: bool, static_path: Path) -> None:
        """Add routes to the web application."""
        routes: list[web.RouteDef | web.StaticDef] = [
            web.static("/static", str(static_path)),
            web.get("/favicon.ico", self._handle_favicon),
            web.get("/restart_{service}", self._handle_restart_service),
            web.get("/server-status", self._handle_partial("server_status")),
            web.get("/bots", self._handle_partial("bots")),
            web.get("/bot/remove/{did}", self._handle_remove_entity("bot")),
            web.get("/clients", self._handle_partial("clients")),
            web.get("/client/remove/{userid}", self._handle_remove_entity("client")),
            web.get("/users", self._handle_partial("users")),
            web.get("/user/remove/{userid}", self._handle_remove_entity("user")),
        ]
        if proxy_mode is True:
            routes.append(web.route("*", "/{path:.*}", self._handle_proxy))
        else:
            routes.extend(
                [
                    web.get("", self._handle_base),
                    web.get("/ca-certificates.tar.gz", single_paths.handle_ca_certificates),
                    web.post("/newauth.do", single_paths.handle_new_auth),
                    web.post("/lookup.do", single_paths.handle_lookup),
                    web.get("/config/Android.conf", single_paths.handle_config_android_conf),
                    web.get("/data_collect/upload/generalData", single_paths.handle_data_collect),
                    web.post("/sa", single_paths.handle_sa),
                    web.post("/v0.1/public/codepush/report_status/deploy", single_paths.handle_codepush_report_status_deploy),
                    web.get("/v0.1/public/codepush/update_check", single_paths.handle_codepush_update_check),
                    web.post("/Global_APP_BuryPoint/api", single_paths.handle_global_app_bury_point_api),
                    web.post("/biz-app-config/api/v2/chat_bot_id/config", single_paths.handle_chat_bot_id_config),
                    web.get("/content/agreement", single_paths.handle_content_agreement),
                ],
            )
            plugins.add_plugins(self._app)
        self._app.add_routes(routes)

    async def start(self) -> None:
        """Start server."""
        try:
            _LOGGER.info("Starting WebServer")
            for binding in self._bindings:
                _LOGGER.info(f"Starting WebServer Server at {binding.host}:{binding.port}")
                runner = web.AppRunner(self._app)
                self._runners.append(runner)
                await runner.setup()

                ssl_ctx: ssl.SSLContext | None = None
                if binding.use_ssl:
                    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    ssl_ctx.load_cert_chain(bumper_isc.server_cert, bumper_isc.server_key)
                    ssl_ctx.load_verify_locations(cafile=bumper_isc.ca_cert)

                site = web.TCPSite(
                    runner,
                    host=binding.host,
                    port=binding.port,
                    ssl_context=ssl_ctx,
                )

                await site.start()
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
            raise

    async def shutdown(self) -> None:
        """Shutdown server."""
        try:
            _LOGGER.info("Shutting down Web Server...")
            for runner in self._runners:
                await runner.shutdown()
                await runner.cleanup()
            self._runners.clear()
            await self._app.shutdown()
            await self._app.cleanup()
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
            raise

    async def _handle_base(self, request: Request) -> Response:
        """Handle the base route."""
        try:
            context = {
                **await self._get_context(),
                **await self._get_context("server_status"),
                **await self._get_context("bots"),
                **await self._get_context("clients"),
                **await self._get_context("users"),
            }
            return aiohttp_jinja2.render_template("home.jinja2", request, context=context)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    def _handle_partial(self, template_name: str) -> Callable[[Request], Awaitable[Response]]:
        async def handler(request: Request) -> Response:
            try:
                context = await self._get_context(template_name)
                return aiohttp_jinja2.render_template(f"partials/{template_name}.jinja2", request, context)
            except Exception:
                _LOGGER.exception(utils.default_exception_str_builder())
            raise HTTPInternalServerError

        return handler

    async def _get_context(self, template_name: str | None = None) -> dict[str, Any]:
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
                        "clients": [client.to_dict() for client in bumper_isc.xmpp_server.clients]
                        if bumper_isc.xmpp_server
                        else [],
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
        return {
            "app_version": bumper_isc.APP_VERSION,
            "github_repo": bumper_isc.GITHUB_REPO,
            "github_release": bumper_isc.GITHUB_RELEASE,
        }

    async def _handle_favicon(self, _: Request) -> web.FileResponse:
        """Serve the favicon.ico file."""
        try:
            favicon_path = Path(str(files("bumper.web").joinpath("static/favicon.ico")))
            if not favicon_path.exists():
                msg = f"Favicon not found at {favicon_path}"
                raise FileNotFoundError(msg)
            return web.FileResponse(path=favicon_path)
        except Exception as e:
            _LOGGER.exception("Failed to serve favicon.ico")
            raise HTTPInternalServerError from e

    async def _handle_restart_service(self, request: Request) -> Response:
        try:
            service = request.match_info.get("service", "")
            if service == "Helperbot":
                if await self._restart_helper_bot():
                    return web.json_response({"status": "complete"})
                return web.json_response({"status": "failed"})
            if service == "MQTTServer":
                if await self._restart_mqtt_server():
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

    async def _restart_mqtt_server(self) -> bool:
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

    async def _restart_helper_bot(self) -> bool:
        if bumper_isc.mqtt_helperbot is not None:
            await bumper_isc.mqtt_helperbot.disconnect()
            await bumper_isc.mqtt_helperbot.start()
            return True
        return False

    def _handle_remove_entity(self, entity_type: str) -> Callable[[Request], Awaitable[Response]]:
        async def handler(request: Request) -> Response:
            try:
                remove_func: Callable[[str], None] | None = None
                get_func: Callable[[str], VacBotClient | VacBotDevice | BumperUser | None] | None = None
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

    async def _handle_proxy(self, request: Request) -> Response:
        try:
            if request.raw_path == "/":
                return await self._handle_base(request)
            if request.raw_path == "/lookup.do":
                return await single_paths.handle_lookup(request)
                # use bumper to handle lookup so bot gets Bumper IP and not Ecovacs

            async with ClientSession(
                headers=request.headers,
                connector=TCPConnector(verify_ssl=False, resolver=utils.get_resolver_with_public_nameserver()),
            ) as session:
                data: Any = None
                json_data: Any = None
                if request.content.total_bytes > 0:
                    read_body = await request.read()
                    _LOGGER_PROXY.info(
                        f"HTTP Proxy Request to EcoVacs (body=true) (URL:{request.url}) :: {read_body.decode('utf-8')}",
                    )
                    if request.content_type == "application/x-www-form-urlencoded":
                        # android apps use form
                        data = await request.post()
                    else:
                        # handle json
                        json_data = await request.json()

                else:
                    _LOGGER_PROXY.info(f"HTTP Proxy Request to EcoVacs (body=false) (URL:{request.url})")

                # Validate and sanitize user-provided input
                validated_url = self._validate_and_sanitize_url(request.url)

                async with session.request(request.method, validated_url, data=data, json=json_data) as resp:
                    if resp.content_type == "application/octet-stream":
                        _LOGGER_PROXY.info(
                            f"HTTP Proxy Response from EcoVacs (URL: {request.url})"
                            f" :: (Status: {resp.status}) :: <BYTES CONTENT>",
                        )
                        return web.Response(body=await resp.read())

                    response = await resp.text()
                    _LOGGER_PROXY.info(
                        f"HTTP Proxy Response from EcoVacs (URL: {request.url}) :: (Status: {resp.status}) :: {response}",
                    )
                    return web.Response(text=response)
        except asyncio.CancelledError:
            _LOGGER_PROXY.exception(f"Request cancelled or timeout :: {request.url}", exc_info=True)
            raise
        except Exception:
            _LOGGER_PROXY.exception(utils.default_exception_str_builder(info="during proxy the request"), exc_info=True)
        raise HTTPInternalServerError

    def _validate_and_sanitize_url(self, url: URL) -> str:
        # Perform URL validation and sanitization here
        # For example, you can check if the URL is in an allowed list
        # and parse it to remove any unwanted components.

        # Sample validation: Check if the host is in an allowed list
        allowed_hosts = {"ecouser.net", "ecovacs.com"}

        if url.host not in allowed_hosts:
            # You may raise an exception or handle it based on your requirements
            msg = "Invalid or unauthorized host"
            raise ValueError(msg)

        # You can also perform additional sanitization if needed
        # For example, remove any query parameters, fragments, etc.
        return str(url.with_query(None).with_fragment(None))
