"""Webserver utils module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from aiohttp import web

from bumper.utils import utils

if TYPE_CHECKING:
    from aiohttp.web_response import Response

# ******************************************************************************

RETURN_API_SUCCESS = "0000"
ERR_ACTIVATE_TOKEN_TIMEOUT = "1006"  # noqa: S105
ERR_COMMON = "0001"
ERR_DEFAULT = "9000"
ERR_EMAIL_NON_EXIST = "1002"
ERR_EMAIL_SEND_TIME_LIMIT = "1011"
ERR_EMAIL_USED = "1001"
ERR_INTERFACE_AUTH = "0002"
ERR_PARAM_INVALID = "0003"
ERR_PWD_WRONG = "1005"  # noqa: S105
ERR_RESET_PWD_TOKEN_TIMEOUT = "1007"  # noqa: S105
ERR_TIMESTAMP_INVALID = "0005"
ERR_TOKEN_INVALID = "0004"  # noqa: S105
ERR_USER_DISABLE = "1004"
ERR_USER_NOT_ACTIVATED = "1003"
ERR_WRONG_CONFIRM_PWD = "10010"  # noqa: S105
ERR_WRONG_EMAIL_ADDRESS = "1008"
ERR_WRONG_PWD_FROMATE = "1009"  # noqa: S105
ERR_UNKNOWN_TODO = "1202"

API_ERRORS: dict[str, str] = {
    RETURN_API_SUCCESS: "0000",
    ERR_ACTIVATE_TOKEN_TIMEOUT: "1006",
    ERR_COMMON: "0001",
    ERR_DEFAULT: "9000",
    ERR_EMAIL_NON_EXIST: "1002",
    ERR_EMAIL_SEND_TIME_LIMIT: "1011",
    ERR_EMAIL_USED: "1001",
    ERR_INTERFACE_AUTH: "0002",
    ERR_PARAM_INVALID: "0003",
    ERR_PWD_WRONG: "1005",
    ERR_RESET_PWD_TOKEN_TIMEOUT: "1007",
    ERR_TIMESTAMP_INVALID: "0005",
    ERR_TOKEN_INVALID: "0004",
    ERR_USER_DISABLE: "1004",
    ERR_USER_NOT_ACTIVATED: "1003",
    ERR_WRONG_CONFIRM_PWD: "10010",
    ERR_WRONG_EMAIL_ADDRESS: "1008",
    ERR_WRONG_PWD_FROMATE: "1009",
    ERR_UNKNOWN_TODO: "1202",
}


# ******************************************************************************


def response_success_v1(data: Any, time: int = utils.get_current_time_as_millis()) -> Response:
    """Get success response with provided data."""
    return web.json_response(
        {
            "code": RETURN_API_SUCCESS,
            "data": data,
            "msg": "The operation was successful",  # 操作成功
            "success": True,
            "time": time,
        },
    )


def response_success_v2(
    data: Any | None = None,
    code: int | None = 0,
    data_key: str = "data",  # data | voices | devices | authCode | code
    result_key: str = "ret",  # result | ret
) -> Response:
    """Response success v2."""
    payload = {
        "todo": "result",
        result_key: "ok",
        data_key: data,
    }
    if data is not None:
        payload[data_key] = data
    if code is not None:
        payload["code"] = code
    return web.json_response(payload)


def response_success_v3(
    code: int = 0,
    data: Any | None = None,
    data_key: str = "data",  # data | voices
    msg: str = "success",  # success | ok
    msg_key: str = "message",  # message | msg
    result: str | dict[str, str] = "ok",
    result_key: str | None = "ret",  # result | ret
    include_success: bool = False,
) -> Response:
    """Response success v3."""
    payload = {
        "code": code,
        msg_key: msg,
    }
    if result_key is not None:
        payload[result_key] = result
    if data is not None:
        payload[data_key] = data
    if include_success:
        payload["success"] = True
    return web.json_response(payload)


def response_success_v4(data: Any, code: int = 0, data_key: str = "data") -> Response:
    """Response success v4."""
    return web.json_response(
        {
            "code": code,
            data_key: data,
        },
    )


# ******************************************************************************


def response_error_v1(msg: str = "Parameter error. Please try again later", code: str = ERR_COMMON) -> Response:
    """Response error v1."""
    return web.json_response(
        {
            "code": code,
            "msg": msg,
            "time": utils.get_current_time_as_millis(),
        },
    )


def response_error_v2(msg: str = "Parameter error. Please try again later", code: str = ERR_COMMON) -> Response:
    """Response error v2."""
    return web.json_response(
        {
            "errno": code,
            "error": msg,
            "result": "fail",
            "todo": "result",
        },
    )


def response_error_v3(msg: str = "Parameter error. Please try again later", code: str = ERR_COMMON) -> Response:
    """Response error v3."""
    return web.json_response(
        {
            "errno": code,
            "error": msg,
            "result": "fail",
            "todo": "result",
        },
    )


def response_error_v4(msg: str = "Parameter error. Please try again later") -> Response:
    """Response error v4."""
    return web.json_response(
        {
            "todo": "result",
            "ret": "fail",
            "errno": msg,
        },
    )


def response_error_v5() -> Response:
    """Response error v5."""
    return web.json_response(
        {
            "todo": "result",
            "ret": "fail",
            "err": 2004,
            "errno": 2004,
            "code": 2004,
        },
    )


def response_error_v6(debug: str, error: str = "Error request, unknown todo") -> Response:
    """Response error v6."""
    return web.json_response(
        {
            "todo": "result",
            "result": "fail",
            "errno": 1,
            "error": error,
            "debug": debug,
        },
    )


def response_error_v7(errno: int = 1, error: str = "unknown") -> Response:
    """Response error v7."""
    return web.json_response(
        {
            "ret": "fail",
            "errno": errno,
            "error": error,
        },
    )


def response_error_v8(request_id: str, error: str) -> Response:
    """Response error v8."""
    return web.json_response(
        {
            "id": request_id,
            "errno": 500,
            "ret": "fail",
            "debug": error,
        },
    )


def response_error_v9(msg: str = "Expired user login", code: str = ERR_TOKEN_INVALID) -> Response:
    """Response error v9."""
    return web.json_response(
        {
            "code": code,
            "msg": msg,
            "time": utils.get_current_time_as_millis(),
            "data": None,
            "success": False,
        },
    )


# ******************************************************************************
# NGIoT (`/api/iot/endpoint/control`) responses.
#
# These differ from the v7/v8 family above: the NGIoT bridge answers HTTP 200
# and carries the outcome in the `x-ngiot-*` headers, with an empty body. The
# app reads those headers, so answering with a JSON body instead makes an
# offline robot indistinguishable from a broken server.
#
# `x-ngiot-fmt: b` is returned even for JSON payloads. That is what the real
# server does on every JSON response - do not "fix" it.

NGIOT_CONTENT_TYPE = "application/octet-stream"
NGIOT_ERRNO_ENDPOINT_OFFLINE = "4200"
NGIOT_ERROR_ENDPOINT_OFFLINE = "endpoint offline"
NGIOT_DEBUG_ENDPOINT_OFFLINE = (
    "jmq.clusterNode.FetchClientInfo rsp==null; no clientinfo in redis which means no ping was received from "
    "endpoint for a long time"
)


def _ngiot_headers(request_id: str | None, ret: str) -> dict[str, str]:
    """Build the `x-ngiot-*` header set for a response."""
    headers = {
        "x-ngiot-fmt": "b",
        "x-ngiot-ret": ret,
    }
    if request_id:
        # The app sends the same opaque value as the `si` query parameter and the
        # `X-ECO-REQUEST-ID` header.
        headers["X-ECO-REQUEST-ID"] = request_id
    return headers


def response_ngiot_success(payload: Any, request_id: str | None = None) -> Response:
    """NGIoT success response, carrying the robot's answer verbatim.

    `x-ngiot-fmt` stays `b` even though the body is JSON, matching observed
    behaviour.
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
    headers = _ngiot_headers(request_id, "error")
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
