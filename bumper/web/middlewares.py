"""Web server middleware module."""

import base64
import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.typedefs import Handler
from aiohttp.web_exceptions import HTTPNoContent
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)


class CustomEncoder(json.JSONEncoder):
    """Custom json encoder, which supports set."""

    def default(self, o: Any) -> Any:
        """Convert objects, which are not supported by the default JSONEncoder."""
        if isinstance(o, set):
            return list(o)
        return json.JSONEncoder.default(self, o)


_EXCLUDE_FROM_LOGGING = [
    "/",
    "/static",
    "/restart_{service}",
    "/server-status",
    "/bots",
    "/bot/remove/{did}",
    "/clients",
    "/client/remove/{resource}",
    "/users",
    "/user/remove/{userid}",
]


@web.middleware
async def log_all_requests(request: Request, handler: Handler) -> StreamResponse:
    """Middleware to log all requests."""
    await _log_debug_request(request)

    if request.match_info.route.resource is None or request.match_info.route.resource.canonical in _EXCLUDE_FROM_LOGGING:
        return await handler(request)

    to_log = {
        "request": {
            "method": request.method,
            "url": str(request.url),
            "path": request.path,
            "query_string": request.query_string,
            "headers": set(request.headers.items()),
            "route_resource": request.match_info.route.resource.canonical,
        },
    }

    try:
        if request.content_length:
            if request.content_type == "application/json":
                to_log["request"]["body"] = await request.json()
            else:
                to_log["request"]["body"] = set(await request.post())

        response: StreamResponse | None = await handler(request)

        if response is None:
            _LOGGER.warning("Response was null!")
            _LOGGER.warning(json.dumps(to_log, cls=CustomEncoder))
            raise HTTPNoContent

        to_log["response"] = {
            "status": f"{response.status}",
            "headers": set(response.headers.items()),
        }

        # Only inspect bodies for concrete in-memory Response objects
        # StreamResponse (and FileResponse) typically don't expose body bytes here.
        body_bytes = getattr(response, "body", None)
        if not (isinstance(response, Response) and body_bytes is not None):
            # Body is not available (streamed or file response) — don't try to read it
            to_log["response"]["body"] = "<streamed or file response; body not available for logging>"
        else:
            if not isinstance(body_bytes, bytes | bytearray):
                try:
                    body_bytes = bytes(body_bytes)
                except Exception:
                    body_bytes = None

            if body_bytes is None:
                return response

            content_type = (getattr(response, "content_type", "") or "").lower()
            content_encoding = response.headers.get("Content-Encoding", "").lower()
            charset = getattr(response, "charset", None)

            is_text_like = (
                content_type.startswith("text")
                or content_type == "application/json"
                or content_type in ("application/javascript", "application/xml", "application/xhtml+xml")
            )
            is_compressed = "gzip" in content_encoding or "deflate" in content_encoding

            if is_compressed or not is_text_like:
                sample_b64 = base64.b64encode(body_bytes[:64]).decode("ascii")
                to_log["response"]["body"] = {
                    "type": "binary",
                    "content_type": content_type,
                    "content_encoding": content_encoding,
                    "length": len(body_bytes),
                    "sample_b64": sample_b64,
                }
            else:
                try:
                    decoded = body_bytes.decode(charset or "utf-8")
                except Exception as decode_err:
                    _LOGGER.debug(
                        f"Failed to decode response body with charset {charset}: {decode_err}; using 'replace' fallback",
                    )
                    decoded = body_bytes.decode(charset or "utf-8", errors="replace")

                if content_type == "application/json":
                    try:
                        to_log["response"]["body"] = json.loads(decoded)
                    except Exception:
                        to_log["response"]["body"] = decoded
                else:
                    to_log["response"]["body"] = decoded

        return response

    except web.HTTPNotFound as e:
        _LOGGER.debug(f"Request path {request.raw_path} not found")
        raise web.HTTPNotFound from e
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during logging the request/response"))
        raise
    finally:
        if bumper_isc.DEBUG_LOGGING_API_REQUEST is True:
            _LOGGER.debug(json.dumps(to_log, cls=CustomEncoder))


async def _log_debug_request(request: Request) -> None:
    try:
        # DEBUG logger by env set to see all requests taken
        # or to print requests which are not know (lists needs to be manually updated)
        if (bumper_isc.DEBUG_LOGGING_API_REQUEST is True) or (
            bumper_isc.DEBUG_LOGGING_API_REQUEST_MISSING is True and utils.check_url_not_used(request.path) is False
        ):
            _LOGGER.info(
                json.dumps(
                    {
                        "warning": "Requested API is not implemented!",
                        "method": request.method,
                        "url": str(request.url),
                        # "host": next((value for key, value in set(request.headers.items()) if key.lower() == "host"), ""),
                        # "path": request.path,
                        # "query_string": request.query_string,
                        "body": await request.text(),
                    },
                    cls=CustomEncoder,
                ),
            )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during logging the debug request"))
