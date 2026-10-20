"""Tests for bumper/web/utils/response_helper.py"""

import json

from bumper.web.utils.response_helper import (
    response_ngiot_ack,
    response_ngiot_offline,
    response_ngiot_success,
)


def _decode(response: object) -> dict[str, object]:
    """Return the JSON body of a response as a dict."""
    body = getattr(response, "body", None)
    if body in (None, b""):
        return {}
    return json.loads(body)


def test_ngiot_success_echoes_request_id_and_keeps_fmt_b() -> None:
    payload = {"header": {"pri": 1}, "body": {"code": 0, "msg": "ok", "data": {"deebotPos": {"x": 1}}}}
    response = response_ngiot_success(payload, "si_abc")

    assert response.status == 200
    assert response.content_type == "application/octet-stream"
    # The real server returns x-ngiot-fmt: b even for JSON bodies. This is
    # observed behaviour, not a bug.
    assert response.headers["x-ngiot-fmt"] == "b"
    assert response.headers["x-ngiot-ret"] == "ok"
    assert response.headers["X-ECO-REQUEST-ID"] == "si_abc"
    assert _decode(response) == payload


def test_ngiot_offline_is_200_with_empty_body_and_errno_4200() -> None:
    response = response_ngiot_offline("si_abc")

    assert response.status == 200
    assert response.body == b""
    assert response.content_type == "application/octet-stream"
    assert response.headers["x-ngiot-errno"] == "4200"
    assert response.headers["x-ngiot-ret"] == "error"
    assert response.headers["X-ECO-REQUEST-ID"] == "si_abc"

    error = json.loads(response.headers["x-ngiot-error"])
    assert error["error"] == "endpoint offline"
    assert "debug" in error


def test_ngiot_offline_omits_request_id_header_when_unknown() -> None:
    response = response_ngiot_offline(None)
    assert "X-ECO-REQUEST-ID" not in response.headers
    assert response.headers["x-ngiot-errno"] == "4200"


def test_ngiot_ack_is_immediate_envelope_without_data() -> None:
    response = response_ngiot_ack("si_abc")

    assert response.status == 200
    assert response.headers["x-ngiot-ret"] == "ok"
    body = _decode(response)
    assert body["body"]["code"] == 0
    assert body["body"]["msg"] == "ok"
    assert "data" not in body["body"]
