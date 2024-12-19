"""Web server module."""

import asyncio
import base64
import dataclasses
import gzip
from importlib.resources import files
import json
import logging
from pathlib import Path
import ssl
from typing import Any

from aiohttp import ClientSession, TCPConnector, web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_urldispatcher import ResourceRoute
import aiohttp_jinja2
import jinja2
from yarl import URL

from bumper.utils import db, dns, utils
from bumper.utils.settings import config as bumper_isc
from bumper.web import middlewares, models, plugins

_LOGGER = logging.getLogger(__name__)
_LOGGER_WEB_LOG = logging.getLogger(f"{__name__}.log")
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

        if isinstance(bindings, WebserverBinding):
            bindings = [bindings]
        self._bindings = bindings

        self._app = web.Application(
            middlewares=[
                middlewares.log_all_requests,
            ],
        )

        templates_path = Path(bumper_isc.bumper_dir) / "bumper" / "web" / "templates"
        if not templates_path.exists():
            templates_path = Path(str(files("bumper.web").joinpath("templates")))

        aiohttp_jinja2.setup(
            self._app,
            loader=jinja2.FileSystemLoader(str(templates_path)),
        )
        self._add_routes(proxy_mode)
        self._app.freeze()  # no modification allowed anymore

    def _add_routes(self, proxy_mode: bool) -> None:
        self._app.add_routes(
            [
                web.get("/bot/remove/{did}", self._handle_remove_bot),
                web.get("/client/remove/{resource}", self._handle_remove_client),
                web.get("/restart_{service}", self._handle_restart_service),
            ],
        )

        if proxy_mode is True:
            self._app.add_routes(
                [
                    web.route("*", "/{path:.*}", self._handle_proxy),
                ],
            )
        else:
            self._app.add_routes(
                [
                    web.get("", self._handle_base),
                    web.post("/lookup.do", self._handle_lookup),
                    web.post("/newauth.do", self._handle_new_auth),
                    web.post("/sa", self._handle_sa),
                    web.get("/config/Android.conf", self._handle_config_android_conf),
                    web.get("/data_collect/upload/generalData", self._handle_data_collect),
                    web.get("/list_routes", self._handle_list_routes),  # NOTE: for dev to check which api's are implemented
                ],
            )
            if bumper_isc.DEBUG_LOGGING_API_ROUTE is True:
                self._app.add_routes(
                    [
                        web.post("/log", self._handle_log),
                    ],
                )
            plugins.add_plugins(self._app)

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
            _LOGGER.info("Shutting down")
            for runner in self._runners:
                await runner.shutdown()
            self._runners.clear()
            await self._app.shutdown()
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
            raise

    async def _handle_base(self, request: Request) -> Response:
        try:
            bots = db.bot_get_all()
            clients = db.client_get_all()
            mq_sessions = []
            if bumper_isc.mqtt_server is not None:
                mq_sessions = [
                    {
                        "username": session.username,
                        "client_id": session.client_id,
                        "state": session.transitions.state,
                    }
                    for session in bumper_isc.mqtt_server.sessions
                ]

            helperbot_connected: bool = False
            if bumper_isc.mqtt_helperbot is not None:
                helperbot_connected = bumper_isc.mqtt_helperbot.is_connected
            mqtt_server_state: str = "stopped"
            if bumper_isc.mqtt_server is not None:
                mqtt_server_state = bumper_isc.mqtt_server.state

            context = {
                "bots": bots,
                "clients": clients,
                "helperbot": {"connected": helperbot_connected},
                "mqtt_server": {
                    "state": mqtt_server_state,
                    "sessions": {
                        "count": len(mq_sessions),
                        "clients": mq_sessions,
                    },
                },
                "xmpp_server": bumper_isc.xmpp_server,
            }
            return aiohttp_jinja2.render_template("home.jinja2", request, context=context)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _restart_helper_bot(self) -> None:
        if bumper_isc.mqtt_helperbot is not None:
            await bumper_isc.mqtt_helperbot.disconnect()
            asyncio.Task(bumper_isc.mqtt_helperbot.start())

    async def _restart_mqtt_server(self) -> None:
        if bumper_isc.mqtt_server is not None:
            await bumper_isc.mqtt_server.shutdown()
            asyncio.Task(bumper_isc.mqtt_server.start())

    async def _handle_restart_service(self, request: Request) -> Response:
        try:
            service = request.match_info.get("service", "")
            if service == "Helperbot":
                await self._restart_helper_bot()
                return web.json_response({"status": "complete"})
            if service == "MQTTServer":
                await self._restart_mqtt_server()
                # In 5 seconds restart Helperbot
                await asyncio.sleep(5)
                await self._restart_helper_bot()
                return web.json_response({"status": "complete"})
            if service == "XMPPServer" and bumper_isc.xmpp_server is not None:
                bumper_isc.xmpp_server.disconnect()
                await bumper_isc.xmpp_server.start_async_server()
                return web.json_response({"status": "complete"})
            return web.json_response({"status": "invalid service"})
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_remove_bot(self, request: Request) -> Response:
        try:
            did = request.match_info.get("did", "")
            db.bot_remove(did)
            if db.bot_get(did):
                return web.json_response({"status": "failed to remove bot"})
            return web.json_response({"status": "successfully removed bot"})
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_remove_client(self, request: Request) -> Response:
        try:
            resource = request.match_info.get("resource", "")
            db.client_remove(resource)
            if db.client_get(resource):
                return web.json_response({"status": "failed to remove client"})
            return web.json_response({"status": "successfully removed client"})
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_lookup(self, request: Request) -> Response:
        try:
            if request.content_type == "application/x-www-form-urlencoded":
                body = await request.post()
            else:
                body = json.loads(await request.text())

            _LOGGER.debug(body)

            if body["todo"] == "FindBest":
                service = body["service"]
                if service == "EcoMsgNew":
                    srv_ip = bumper_isc.bumper_announce_ip
                    srv_port = bumper_isc.XMPP_LISTEN_PORT_TLS
                    _LOGGER.info(f"Announcing EcoMsgNew Server to bot as: {srv_ip}:{srv_port}")
                    server = json.dumps({"ip": srv_ip, "port": srv_port, "result": "ok"})
                    # NOTE: bot seems to be very picky about having no spaces, only way was with text
                    server = server.replace(" ", "")
                    return web.json_response(text=server)

                if service == "EcoUpdate":
                    srv_ip = bumper_isc.ECOVACS_UPDATE_SERVER
                    srv_port = bumper_isc.ECOVACS_UPDATE_SERVER_PORT
                    _LOGGER.info(f"Announcing EcoUpdate Server to bot as: {srv_ip}:{srv_port}")
                    return web.json_response({"result": "ok", "ip": srv_ip, "port": srv_port})

            return web.json_response({})

        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_new_auth(self, request: Request) -> Response:
        try:
            if request.content_type == "application/x-www-form-urlencoded":
                post_body = await request.post()
            else:
                post_body = json.loads(await request.text())
            _LOGGER.debug(post_body)
            todo = post_body.get("todo", "")
            if todo == "OLoginByITToken":
                # NOTE: Bumper is only returning the submitted token. No reason yet to create another new token
                return web.json_response(
                    {
                        "authCode": post_body.get("itToken"),
                        "result": "ok",
                        "todo": "result",
                    },
                )
            return web.json_response(
                {
                    "errno": models.ERR_UNKOWN_TODO,
                    "result": "fail",
                    "error": "Error request, unknown todo",
                    "todo": "result",
                },
            )
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_sa(self, request: Request) -> Response:
        try:
            if bumper_isc.DEBUG_LOGGING_SA_RESULT is True:
                if request.content_type == "application/x-www-form-urlencoded":
                    post_body = await request.post()
                else:
                    post_body = json.loads(await request.text())

                post_body_gzip = str(post_body.get("gzip", 0))
                data_list = post_body.get("data_list")
                if post_body_gzip == "1" and isinstance(data_list, str):
                    decoded_data = base64.b64decode(data_list)
                    decompressed_data = gzip.decompress(decoded_data).decode("utf-8")
                    _LOGGER.info(decompressed_data)
            return web.json_response(None)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_config_android_conf(self, _: Request) -> Response:
        # TODO: check what's needed to be implemented
        utils.default_log_warn_not_impl("_handle_config_android_conf")
        try:
            return web.json_response(
                {
                    "v": "v1",
                    "configs": {"disableSDK": False, "disableDebugMode": False},
                },
            )
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_data_collect(self, _: Request) -> Response:
        # TODO: check what's needed to be implemented
        utils.default_log_warn_not_impl("_handle_data_collect")
        try:
            return web.json_response(None)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
        raise HTTPInternalServerError

    async def _handle_proxy(self, request: Request) -> Response:
        try:
            if request.raw_path == "/":
                return await self._handle_base(request)
            if request.raw_path == "/lookup.do":
                return await self._handle_lookup(request)
                # use bumper to handle lookup so bot gets Bumper IP and not Ecovacs

            async with ClientSession(
                headers=request.headers,
                connector=TCPConnector(verify_ssl=False, resolver=dns.get_resolver_with_public_nameserver()),
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

    async def _handle_log(self, request: Request) -> Response:
        to_log = {}
        try:
            to_log.update(
                {
                    "query_string": request.query_string,
                    "headers": set(request.headers.items()),
                },
            )
            if request.content_length:
                to_log["body"] = set(await request.post())
        except Exception:
            _LOGGER_WEB_LOG.exception(utils.default_exception_str_builder(info="during logging the request"), exc_info=True)
        finally:
            _LOGGER_WEB_LOG.info(json.dumps(to_log, cls=middlewares.CustomEncoder))
        return web.Response()

    async def _handle_list_routes(self, _: Request) -> Response:
        try:
            routes = []
            for route in self._app.router.routes():
                if isinstance(route, ResourceRoute):
                    resource = route.resource
                    if resource is not None:
                        path: Any | None = resource.get_info().get("formatter") or resource.get_info().get("path")
                        routes.append(
                            {
                                "method": route.method,
                                "path": path,
                            },
                        )
            return web.json_response(routes)
        except Exception:
            _LOGGER_WEB_LOG.exception(utils.default_exception_str_builder(info="during create api list"), exc_info=True)
        return web.Response()
