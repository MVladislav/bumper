"""Web server middleware module."""

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
    "/bot/remove/{did}",
    "/client/remove/{resource}",
    "/restart_{service}",
]


@web.middleware
async def log_all_requests(request: Request, handler: Handler) -> StreamResponse:
    """Middleware to log all requests."""
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
        try:
            if request.content_length:
                if request.content_type == "application/json":
                    to_log["request"]["body"] = await request.json()
                else:
                    to_log["request"]["body"] = set(await request.post())
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during logging the request"))
            raise

        response: StreamResponse | None = await handler(request)

        try:
            if response is None:
                _LOGGER.warning("Response was null!")
                _LOGGER.warning(json.dumps(to_log, cls=CustomEncoder))
                raise HTTPNoContent

            to_log["response"] = {
                "status": f"{response.status}",
                "headers": set(response.headers.items()),
            }

            if isinstance(response, Response) and response.body:
                if response.text is None:
                    msg = "Response text is not provided."
                    raise ValueError(msg)

                if response.content_type == "application/json":
                    to_log["response"]["body"] = json.loads(response.text)
                elif response.content_type.startswith("text"):
                    to_log["response"]["body"] = response.text

            return response
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder(info="during logging the response"))
            raise

    except web.HTTPNotFound:
        _LOGGER.debug(f"Request path {request.raw_path} not found")
        raise
    finally:
        _LOGGER.debug(json.dumps(to_log, cls=CustomEncoder))
