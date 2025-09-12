"""Single paths for bumper web server."""

import base64
import gzip
import hashlib
import io
import json
import logging
from pathlib import Path
import tarfile

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError, HTTPNotFound
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import get_new_auth
from bumper.web.response_utils import ERR_UNKNOWN_TODO, response_error_v2, response_success_v3

_LOGGER = logging.getLogger(__name__)


async def handle_ca_certificates(_: Request) -> Response:
    """Handle CA Certificates (/ca-certificates.tar.gz)."""
    try:
        if bumper_isc.CA_CERTS_API_ENABLED is False:
            raise HTTPNotFound(text="CA certificate download endpoint is disabled.")

        ca_cert_path: Path = bumper_isc.ca_cert
        ca_cert_path_original: Path = Path(__file__).parent / "static" / "certs" / "ca-certificates-original.crt"

        if not ca_cert_path.exists():
            msg = f"CA cert file not found: {ca_cert_path}"
            _LOGGER.error(msg)
            raise HTTPNotFound(text=msg)

        # Read self-signed cert
        try:
            cert_a = ca_cert_path.read_bytes()
        except FileNotFoundError as e:
            _LOGGER.exception("Self-signed CA cert not found")
            raise HTTPNotFound(text=str(e)) from e
        except OSError as e:
            _LOGGER.exception("OS error while reading self-signed CA cert")
            raise HTTPInternalServerError from e

        if bumper_isc.CA_CERTS_API_DISABLE_COMBINE:
            # Only self-signed CA
            combined = cert_a
        else:
            # Need original cert as well
            if not ca_cert_path_original.exists():
                msg = f"Original CA cert file not found: {ca_cert_path_original}"
                _LOGGER.error(msg)
                raise HTTPNotFound(text=msg)

            try:
                cert_b = ca_cert_path_original.read_bytes()
            except FileNotFoundError as e:
                _LOGGER.exception("Original CA cert not found")
                raise HTTPNotFound(text=str(e)) from e
            except OSError as e:
                _LOGGER.exception("OS error while reading original CA cert")
                raise HTTPInternalServerError from e

            # Combine with one newline
            if not cert_a.endswith(b"\n"):
                cert_a += b"\n"
            combined = cert_a + cert_b

        # Compute md5 of the final bundle
        md5_hash = hashlib.md5(combined).hexdigest()  # noqa: S324

        # Build tar.gz in-memory
        buf = io.BytesIO()
        try:
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                # Add the CA bundle
                crt_name = "ca-certificates/ca-certificates.crt"
                crt_info = tarfile.TarInfo(name=crt_name)
                crt_info.size = len(combined)
                tar.addfile(crt_info, io.BytesIO(combined))

                md5_text = f"{md5_hash}\n".encode()
                md5_info = tarfile.TarInfo(name="ca-certificates/MD5SUMS")
                md5_info.size = len(md5_text)
                tar.addfile(md5_info, io.BytesIO(md5_text))
        except Exception as e:
            _LOGGER.exception("Failed building tar.gz archive for CA certificates")
            raise HTTPInternalServerError from e

        buf.seek(0)
        data = buf.getvalue()

        headers = {
            "Content-Disposition": 'attachment; filename="ca-certificates.tar.gz"',
            "Content-Type": "application/gzip",
            "Content-Length": str(len(data)),
        }
        return Response(body=data, headers=headers)

    except web.HTTPException:
        raise
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_new_auth(request: Request) -> Response:
    """Handle new auth (/newauth.do)."""
    try:
        post_body = json.loads(await request.text())

        todo = post_body.get("todo", "")
        if todo == "OLoginByITToken":
            return await get_new_auth(request)

        _LOGGER.warning(f"todo is not know :: {todo!s}")
        return response_error_v2(msg="Error request, unknown todo", code=ERR_UNKNOWN_TODO)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_lookup(request: Request) -> Response:
    """Handle lookup (/lookup.do)."""
    try:
        if request.content_type == "application/x-www-form-urlencoded":
            post_body = await request.post()
        else:
            post_body = json.loads(await request.text())

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
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_data_collect(_: Request) -> Response:
    """Handle data collect (/data_collect/upload/generalData)."""
    try:
        return web.json_response(None)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder())
    raise HTTPInternalServerError


async def handle_sa(request: Request) -> Response:
    """Handle SA command (/sa)."""
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


async def handle_codepush_report_status_deploy(_: Request) -> Response:
    """Codepush Report Status Deploy (/v0.1/public/codepush/report_status/deploy)."""
    return response_success_v3(result_key=None, msg_key="msg")


async def handle_codepush_update_check(request: Request) -> Response:
    """CodePush Update check (/v0.1/public/codepush/update_check)."""
    deployment_key = request.query.get("deployment_key", "")
    response = {
        "update_info": {
            "download_url": "",
            "description": "",
            "is_available": False,
            "is_disabled": True,
            "target_binary_range": "",
            "label": "",
            "package_hash": "",
            "package_size": 0,
            "should_run_binary_version": False,
            "update_app_version": False,
            "is_mandatory": False,
        },
    }
    if deployment_key == "RSYAx668chaf0tpKvf1kJNaVJmDzi4g83wsg78":  # pragma: allowlist secret
        response = {
            "update_info": {
                "download_url": "https://ecovacs-na-codepush.s3.us-west-1.amazonaws.com/FrxqD9fvyTZqY8umUP3kTEfGSTMl",
                "description": '"1.0.0-"',
                "is_available": True,
                "is_disabled": False,
                "target_binary_range": "1.0.0",
                "label": "v5",
                "package_hash": "df903c2d7db36907cdd31d583f68c125e49ecc03941fe360661803f3d92fe158",  # pragma: allowlist secret
                "package_size": 1859843,
                "should_run_binary_version": False,
                "update_app_version": False,
                "is_mandatory": True,
            },
        }
    elif deployment_key == "0XLlHQNfNd0YUpiD-gDe1h6oIctlsVKwpcmViH":  # pragma: allowlist secret
        response = {
            "update_info": {
                "download_url": "https://ecovacs-na-codepush.s3.us-west-1.amazonaws.com/lp9Tb7HxQCVq1kjtuLn1fbBm6qhz",
                "description": '"1.0.0-"',
                "is_available": True,
                "is_disabled": False,
                "target_binary_range": "1.0.0",
                "label": "v5",
                "package_hash": "64c5e72612ed6c19d51f2c8341c016e5942028a3e1e04d24bbfef224f05ee2cc",  # pragma: allowlist secret
                "package_size": 8342889,
                "should_run_binary_version": False,
                "update_app_version": False,
                "is_mandatory": True,
            },
        }

    return web.json_response(response)


async def handle_global_app_bury_point_api(_: Request) -> Response:
    """Codepush Report Status Deploy (/Global_APP_BuryPoint/api)."""
    return web.json_response(
        {
            "header": {
                "result_code": "000000",
            },
            "body": {},
        },
        # {
        #     "header": {
        #         "result_msg": "Authentifizierung der Schnittstelle fehlgeschlagen",  # 接口鉴权失败
        #         "result_code": "100001",
        #     },
        #     "body": {},
        # },
    )


async def handle_chat_bot_id_config(_: Request) -> Response:
    """Handle chat bot ID config (/biz-app-config/api/v2/chat_bot_id/config)."""
    return response_success_v3(
        msg_key="msg",
        data={
            "chat_bot_id": "yiko_full_stack_en",
            "introduction": "Welcome to use the smart assistant",
            "lang": "en",
        },
    )


async def handle_content_agreement(_: web.Request) -> web.Response:
    """Content Agreement (/content/agreement)."""
    html_content = """
    <div style="font-family: Arial, sans-serif; margin: 2rem auto; padding: 1em;
    border: 2px dashed #ccc; border-radius: 10px; background-color: #f9f9f9; font-size: 2rem; max-width: 52rem;">
      <h2 style="text-align: center;">Welcome to Bumper 🚗💨</h2>
      <p><strong>Mini User-ish Agreement</strong></p>
      <ul>
        <li>
            <strong>You break it, you fix it.</strong>
            We built it, you run it. If it breaks, blame your last caffeine-fueled update.
        </li>
        <li>
            <strong>Your data is yours.</strong>
            We can't see it. We don't want it. Bumper runs at home. It's antisocial like that.
        </li>
        <li>
            <strong>No cloud, no cry.</strong>
            If things go wrong, check your Wi-Fi, cat, or moon phase. Probably not our fault.
        </li>
        <li>
            <strong>Support not included.</strong>
            Ask your future self or consult the ancient scrolls (aka README.md).
        </li>
        <li>
            <strong>No evil bots.</strong>
            Don't use Bumper for villainy. Floors, yes. World domination, no.
        </li>
      </ul>
      <p style="text-align: center; font-style: italic;">
        By using Bumper, you accept responsibility and the eternal right to brag about your local setup. 🍕
      </p>
    </div>
    """
    return web.Response(text=html_content, content_type="text/html")
