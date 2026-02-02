"""Web server module."""

import asyncio
import dataclasses
from importlib.resources import files
import logging
from pathlib import Path
import ssl
from typing import Any

from aiohttp import ClientSession, TCPConnector, web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_jinja2
import jinja2
from yarl import URL

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import middlewares, plugins, single_paths, web_paths

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
        static_path = self._resolve_path("static_web")

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
            web.get("", web_paths.handle_base),
            web.get("/favicon.ico", web_paths.handle_favicon),
            web.get("/restart_{service}", web_paths.handle_restart_service),
            web.get("/server-status", web_paths.handle_partial("server_status")),
            web.get("/bots", web_paths.handle_partial("bots")),
            web.get("/bot/remove/{did}", web_paths.handle_remove_entity("bot")),
            web.get("/clients", web_paths.handle_partial("clients")),
            web.get("/client/remove/{userid}", web_paths.handle_remove_entity("client")),
            web.get("/users", web_paths.handle_partial("users")),
            web.get("/user/remove/{userid}", web_paths.handle_remove_entity("user")),
            web.get("/clean_logs", web_paths.handle_partial("clean_logs")),
            web.get("/clean_log/remove/{clean_log_id}", web_paths.handle_remove_entity("clean_log")),
            web.get("/clean_logs/remove/{placeholder}", web_paths.handle_remove_entity("clean_logs")),
        ]
        if proxy_mode is True:
            routes.append(web.route("*", "/{path:.*}", self._handle_proxy))
        else:
            routes.extend(
                [
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

    async def _handle_proxy(self, request: Request) -> Response:
        try:
            if request.raw_path == "/":
                return await web_paths.handle_base(request)
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
