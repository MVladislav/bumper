"""Single paths for bumper web server."""

import base64
from functools import cache
import gzip
import hashlib
import io
import json
import logging
from pathlib import Path
import tarfile
from typing import Any
from urllib.parse import unquote

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError, HTTPNotFound
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import get_new_auth
from bumper.web.context import read_body
from bumper.web.envelope import (
    ERR_UNKNOWN_TODO,
    LEGACY_BARE,
    LEGACY_NO_RET,
    ApiError,
)
from bumper.web.payloads import codepush_update_check

_LOGGER = logging.getLogger(__name__)


async def handle_ca_certificates(_: Request) -> Response:
    """Handle CA Certificates (/ca-certificates.tar.gz)."""
    try:
        return Response(
            body=_build_ca_archive(),
            content_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{bumper_isc.ca_archive_filename}"'},
        )
    except web.HTTPException as e:
        return Response(status=e.status, text=e.text, content_type="text/plain")
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


@cache
def _build_ca_archive() -> bytes:
    """Build the CA archive once per process.

    The bundle changes only when the certificates are regenerated, which needs
    a restart, so rebuilding it on every request would only cost time.
    """
    _LOGGER.debug("Building CA certificates archive")

    ca_cert_path: Path = bumper_isc.ca_cert
    ca_cert_path_original: Path = Path(__file__).parent / "static_web" / "certs" / "ca-certificates-original.crt"

    cert_bumper = _get_ca_cert(ca_cert_path)
    if bumper_isc.CA_CERT_API_ONLY_BUMPER_CERT:
        cert_result = cert_bumper
    else:
        certs_ecovacs = _get_ca_cert(ca_cert_path_original)
        if not cert_bumper.endswith(b"\n"):
            cert_bumper += b"\n"
        cert_result = cert_bumper + certs_ecovacs

    md5_hash = hashlib.md5(cert_result).hexdigest()  # noqa: S324

    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        crt_name = "ca-certificates/ca-certificates.crt"
        crt_info = tarfile.TarInfo(name=crt_name)
        crt_info.size = len(cert_result)
        tar.addfile(crt_info, io.BytesIO(cert_result))

        md5_text = f"{md5_hash}\n".encode()
        md5_info = tarfile.TarInfo(name="ca-certificates/MD5SUMS")
        md5_info.size = len(md5_text)
        tar.addfile(md5_info, io.BytesIO(md5_text))

    return archive.getvalue()


def _get_ca_cert(cert_path: Path) -> bytes:
    if not cert_path.exists():
        msg = f"CA cert file not found: {cert_path}"
        _LOGGER.error(msg)
        raise HTTPNotFound(text=msg)

    try:
        return cert_path.read_bytes()
    except OSError as e:
        _LOGGER.exception(f"OS error while reading CA cert: {cert_path}")
        raise HTTPInternalServerError from e


async def handle_new_auth(request: Request) -> Any:
    """Handle new auth (/newauth.do)."""
    try:
        post_body = await read_body(request)

        todo = post_body.get("todo", "")
        if todo == "OLoginByITToken":
            return await get_new_auth(request)

        _LOGGER.warning(f"todo is not know :: {todo!s}")
        msg = "Error request, unknown todo"
        raise ApiError(msg=msg, code=ERR_UNKNOWN_TODO)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_lookup(request: Request) -> Response:
    """Handle lookup (/lookup.do)."""
    try:
        post_body = await read_body(request)

        todo = post_body.get("todo", "")
        if todo == "FindBest":
            service = post_body.get("service", "")
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
            _LOGGER.warning(f"service is not know :: {service!s}")
        _LOGGER.warning(f"todo is not know :: {todo!s}")

        return web.json_response({})
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_config_android_conf(_: Request) -> Response:
    """Handle config android conf (/config/Android.conf)."""
    try:
        return web.json_response(
            {
                "v": "v1",
                "configs": {"disableSDK": False, "disableDebugMode": False},
            },
        )
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


def _parse_upload_meta(raw: str) -> dict[str, Any]:
    """Parse the `meta` query parameter, which is a URL-encoded JSON object."""
    if not raw:
        return {}
    try:
        parsed = json.loads(unquote(raw))
    except ApiError:
        raise
    except Exception:
        _LOGGER.warning("Camera upload meta is not valid URL-encoded JSON")
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def handle_sa(request: Request) -> Response:
    """Handle SA command (/sa)."""
    try:
        if bumper_isc.DEBUG_LOGGING_SA_RESULT is True:
            post_body = await read_body(request)

            post_body_gzip = str(post_body.get("gzip", 0))
            data_list = post_body.get("data_list")
            if post_body_gzip == "1" and isinstance(data_list, str):
                decoded_data = base64.b64decode(data_list)
                decompressed_data = gzip.decompress(decoded_data).decode("utf-8")
                _LOGGER.info(decompressed_data)
        return web.json_response(None)
    except ApiError:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_codepush_report_status_deploy(_: Request) -> Response:
    """Codepush Report Status Deploy (/v0.1/public/codepush/report_status/deploy)."""
    body: dict[str, Any] = LEGACY_BARE.with_msg(("msg", "success")).render()
    return web.json_response(body)


async def handle_codepush_update_check(request: Request) -> Response:
    """CodePush Update check (/v0.1/public/codepush/update_check)."""
    response = codepush_update_check(
        deployment_key=request.query.get("deployment_key", ""),
        label=request.query.get("label", ""),
        package_hash=request.query.get("package_hash", ""),
        package_name=request.query.get("package_name"),
        app_version=request.query.get("app_version", "1.0.0"),
        deployment_name=request.query.get("deployment_name", "Production"),
    )
    return web.json_response(response)


async def handle_global_app_bury_point_api(_: Request) -> Response:
    """Global APP BuryPoint API (/Global_APP_BuryPoint/api)."""
    return web.json_response(
        {
            "header": {
                "result_code": "000000",
            },
            "body": {},
        },
    )


async def handle_global_app_bury_point_api_appevent(_: Request) -> Response:
    """Global APP BuryPoint API app-event (/Global_APP_BuryPoint/api/appevent)."""
    return web.json_response(
        {
            "header": {
                "result_code": "000000",
            },
            "body": {},
        },
    )


async def handle_chat_bot_id_config(_: Request) -> Response:
    """Handle chat bot ID config (/biz-app-config/api/v2/chat_bot_id/config)."""
    return web.json_response(
        LEGACY_NO_RET.with_msg(("msg", "success")).render(
            {
                "chat_bot_id": "yiko_full_stack_en",
                "introduction": "Welcome to use the smart assistant",
                "lang": "en",
            },
        ),
    )
