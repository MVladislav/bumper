"""The NGIoT bridge.

`/api/iot/endpoint/control` does not answer with a JSON envelope: it
answers http 200 with an empty body and carries the outcome in the
`x-ngiot-*` headers. The app reads those headers, so answering with a JSON
body instead makes an offline robot indistinguishable from a broken server.

This is a transport, not one of the JSON families, so it does not live with
the templates.
"""

import json
import logging

from aiohttp import web
from aiohttp.web_response import Response

from bumper.utils import utils

_LOGGER = logging.getLogger(__name__)

NGIOT_CONTENT_TYPE = "application/octet-stream"
# The errno of a robot that is not reachable. The NGIoT bridge carries it
# in a header, where every value is a string; the legacy bridge carries it
# in the body, where it is a number.
ERRNO_ENDPOINT_OFFLINE = 4200
NGIOT_ERRNO_ENDPOINT_OFFLINE = str(ERRNO_ENDPOINT_OFFLINE)
NGIOT_ERROR_ENDPOINT_OFFLINE = "endpoint offline"
NGIOT_DEBUG_ENDPOINT_OFFLINE = (
    "jmq.clusterNode.FetchClientInfo rsp==null; no clientinfo in redis which means no ping was received from "
    "endpoint for a long time"
)


def _ngiot_headers(request_id: str | None, ret: str, body: bool = True) -> dict[str, str]:
    """Build the `x-ngiot-*` header set for a response."""
    headers = {
        "x-ngiot-ret": ret,
    }
    if body:
        headers["x-ngiot-fmt"] = "b"
    if request_id:
        # The app sends the same opaque value as the `si` query parameter and the
        # `X-ECO-REQUEST-ID` header.
        headers["X-ECO-REQUEST-ID"] = request_id
    return headers


def response_ngiot_success(payload: object, request_id: str | None = None) -> Response:
    """NGIoT success response, carrying the robot's answer verbatim.

    `x-ngiot-fmt` stays `b` even though the body is JSON.
    """
    return web.Response(
        body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        content_type=NGIOT_CONTENT_TYPE,
        charset="utf-8",
        headers=_ngiot_headers(request_id, "ok"),
    )


def response_ngiot_ack(request_id: str | None = None) -> Response:
    """NGIoT acknowledgement for the fire-and-forget variant (`ct=m`).

    Shape is inferred from the request/response variant: same success headers,
    an envelope carrying `code: 0` and no data, because the caller does not wait
    for the robot. `tzm` is deliberately omitted - `utils.get_tzm_and_ts()`
    raises by design when the configured local timezone is UTC, and this path
    must not fail for that reason. The shape is inferred, not confirmed.
    """
    envelope = {
        "header": {
            "pri": 1,
            "ts": utils.get_current_time_as_millis(),
            "ver": "0.0.1",
        },
        "body": {"code": 0, "msg": "ok"},
    }
    return response_ngiot_success(envelope, request_id)


def response_ngiot_offline(request_id: str | None = None) -> Response:
    """NGIoT response for an endpoint the robot is not reachable on.

    HTTP 200 with an empty body and the `x-ngiot-errno: 4200` header set, which
    is how the real server reports an offline robot. The app renders this as
    "offline"; an `errno 500` JSON body does not.
    """
    headers = _ngiot_headers(request_id, "error", body=False)
    headers["x-ngiot-errno"] = NGIOT_ERRNO_ENDPOINT_OFFLINE
    headers["x-ngiot-error"] = json.dumps(
        {"error": NGIOT_ERROR_ENDPOINT_OFFLINE, "debug": NGIOT_DEBUG_ENDPOINT_OFFLINE},
        separators=(",", ":"),
    )
    return web.Response(
        body=b"",
        content_type=NGIOT_CONTENT_TYPE,
        charset="utf-8",
        headers=headers,
    )
