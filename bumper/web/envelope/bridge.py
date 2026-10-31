"""The answers of the legacy bridge.

The legacy bridge (`/api/iot/devmanager.do`) answers with a JSON body, in
contrast to the NGIoT bridge, which answers with headers.
"""

from aiohttp import web
from aiohttp.web_response import Response

from .ngiot import ERRNO_ENDPOINT_OFFLINE, NGIOT_DEBUG_ENDPOINT_OFFLINE, NGIOT_ERROR_ENDPOINT_OFFLINE


def response_error_endpoint_offline() -> Response:
    """Answer the way the legacy bridge does when the robot is not reachable.

    It answers `{"ret": "fail", "errno": 4200, "error": "endpoint offline",
    "debug": …}`. The NGIoT bridge reports the same condition with headers
    and an empty body instead, see `response_ngiot_offline`.
    """
    return web.json_response(
        {
            "ret": "fail",
            "errno": ERRNO_ENDPOINT_OFFLINE,
            "error": NGIOT_ERROR_ENDPOINT_OFFLINE,
            "debug": NGIOT_DEBUG_ENDPOINT_OFFLINE,
        },
    )
