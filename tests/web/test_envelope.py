"""Tests for bumper/web/envelope/"""

import json

import pytest

from bumper.web.envelope import (
    GL_V1,
    LEGACY,
    LEGACY_BARE,
    TODO_RET,
    ApiError,
    response_error_endpoint_offline,
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


def test_gl_v1_stamps_the_current_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """The time is stamped per call, not frozen when the module was imported.

    The app reads the time to learn the clock offset when an answer carries
    `code == "0005"`. A stamp frozen at import is wrong once the server runs.
    """
    monkeypatch.setattr("bumper.web.envelope.templates.utils.get_current_time_as_millis", lambda: 1_700_000_000_000)

    body = GL_V1.render({"a": 1})

    assert body["time"] == 1_700_000_000_000


def test_gl_v1_accepts_a_fixed_time() -> None:
    """The timestamp endpoint reports a time of its own."""
    body = GL_V1.with_time(42).render({"timestamp": 42})

    assert body["time"] == 42
    assert body["data"] == {"timestamp": 42}


def test_gl_v1_carries_the_success_message() -> None:
    """The success answer carries a readable message.

    The API default is Chinese; Bumper answers in English, which the app does
    not read on success.
    """
    body = GL_V1.render(None)

    assert body["msg"] == "Operation Successful"
    assert body["code"] == "0000"
    assert body["success"] is True


def test_the_families_render_their_own_shape() -> None:
    """Every family produces the keys its template declares."""
    assert set(LEGACY.render({"a": 1})) == {"code", "message", "ret", "data"}
    assert set(LEGACY_BARE.render({"a": 1})) == {"code", "data"}
    assert set(TODO_RET.render({"a": 1})) == {"code", "todo", "ret", "data"}


def test_an_error_takes_the_shape_of_its_family() -> None:
    """A failure is shaped by the family the endpoint is bound to."""
    error = ApiError(msg="no user", code="0004")

    body = GL_V1.error.render(error.code, error.msg)

    assert body["code"] == "0004"
    assert body["msg"] == "no user"
    assert body["success"] is False


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
    # The header describes the body, and this answer has none.
    assert "x-ngiot-fmt" not in response.headers

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


def test_endpoint_offline_is_reported_in_the_body() -> None:
    """The legacy bridge reports an offline robot in the body.

    `/api/iot/devmanager.do` answers
    `{"ret": "fail", "errno": 4200, "error": "endpoint offline", "debug": …}`.
    """
    body = _decode(response_error_endpoint_offline())

    assert body["ret"] == "fail"
    assert body["errno"] == 4200
    assert body["error"] == "endpoint offline"
    assert "debug" in body
