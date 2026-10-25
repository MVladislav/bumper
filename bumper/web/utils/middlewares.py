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
from bumper.web.envelope import ERR_COMMON, GL_V1, LEGACY, ApiError, Template

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
    "/client/remove/{userid}",
    "/users",
    "/user/remove/{userid}",
]


@web.middleware
async def shape_failures(request: Request, handler: Handler) -> StreamResponse:
    """Answer a request that failed in the shape of its family.

    Two failures are not shaped by the endpoint itself: a request that
    matched no route, and a failure that a handler raised without a shape.
    An html page or a stack trace makes the app unable to tell "Bumper does
    not implement this" from "Bumper is broken", so the answer is an
    envelope. The family follows the path: the private API of the `gl-*`
    generation answers with the `code`/`msg` shape, everything else with the
    `code`/`message` one.
    """
    try:
        return await handler(request)
    except web.HTTPNotFound:
        body: dict[str, Any] = _template_of(request).error.render(code=ERR_COMMON, msg="Not found")
        return web.json_response(body, status=404)
    except ApiError as err:
        # The handler raised a failure and did not shape it itself, so the
        # shape of the family of the path is used.
        body = _template_of(request).error.render(err.code, err.msg, err.debug)
        return web.json_response(body)


def _template_of(request: Request) -> Template:
    """Return the shape of the family the path belongs to."""
    return GL_V1 if request.path.startswith(("/v1/", "/v2/", "/v3/")) else LEGACY


@web.middleware
async def log_all_requests(request: Request, handler: Handler) -> StreamResponse:
    """Middleware to log all requests."""
    await _log_debug_request(request)

    if request.match_info.route.resource is None or request.match_info.route.resource.canonical in _EXCLUDE_FROM_LOGGING:
        return await handler(request)
    if bumper_isc.DEBUG_LOGGING_API_REQUEST is False:
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
                try:
                    to_log["request"]["body"] = await request.json()
                except Exception:
                    _LOGGER.debug("Failed to decode body as json")
                    to_log["request"]["body"] = await _body_of(request)
            else:
                to_log["request"]["body"] = await _body_of(request)

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
            # Body is not available (streamed or file response) - don't try to read it
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

    except web.HTTPNotFound as e:
        _LOGGER.debug(f"Request path {request.raw_path} not found")
        raise web.HTTPNotFound from e
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during logging the request/response"))
        raise

    _LOGGER.debug(json.dumps(to_log, cls=CustomEncoder))
    return response


async def _body_of(request: Request) -> str:
    """Return the body of a request as text.

    A body is not always text: a map, a firmware, an image - the bytes are
    decoded with the errors replaced, so that the logging never fails on a
    body it cannot read.
    """
    body = await request.read()
    return body.decode("utf-8", errors="replace")


async def _log_debug_request(request: Request) -> None:
    try:
        not_covered = request.match_info.route.resource is None
        # DEBUG logger by env set to see all requests taken
        # or to print requests which do not match a registered route
        if (bumper_isc.DEBUG_LOGGING_API_REQUEST is True) or (
            bumper_isc.DEBUG_LOGGING_API_REQUEST_MISSING is True and not_covered
        ):
            body = await _body_of(request)
            _LOGGER.info(
                json.dumps(
                    {
                        "warning": "Requested API is not implemented!" if not_covered else "Request debug",
                        "not_covered": not_covered,
                        "method": request.method,
                        "url": str(request.url),
                        # "host": next((value for key, value in set(request.headers.items()) if key.lower() == "host"), ""),
                        # "path": request.path,
                        # "query_string": request.query_string,
                        "body": body,
                    },
                    cls=CustomEncoder,
                ),
            )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during logging the debug request"))
