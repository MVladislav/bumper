"""Tests for bumper.web.context."""

from unittest import mock
from urllib.parse import urlencode

from aiohttp.streams import StreamReader
from aiohttp.test_utils import make_mocked_request
import jwt

from bumper.utils.settings import config as bumper_isc
from bumper.web.context import (
    BODY,
    CLAIMS,
    claimed_userid,
    claims,
    device_id,
    read_body,
    verified_claims,
)


def _stream(body: bytes = b"") -> StreamReader:
    """Build a StreamReader carrying ``body``."""
    protocol = mock.Mock()
    protocol.max_field_size = 8190
    transport = mock.Mock()
    transport.get_extra_info.return_value = None
    protocol.transport = transport
    reader = StreamReader(protocol, 2**16)
    if body:
        reader.feed_data(body)
    reader.feed_eof()
    return reader


def _request(
    *,
    method: str = "POST",
    path: str = "/",
    query: str = "",
    body: bytes = b"",
    content_type: str = "application/json",
    headers: dict[str, str] | None = None,
    match_info: dict[str, str] | None = None,
) -> object:
    full_path = path if not query else f"{path}?{query}"
    hdrs = {"Content-Type": content_type}
    if headers:
        hdrs.update(headers)
    return make_mocked_request(
        method,
        full_path,
        headers=hdrs,
        payload=_stream(body),
        match_info=match_info or {},
    )


async def test_read_body_cached() -> None:
    request = _request()
    request[BODY] = {"cached": True}  # type: ignore[index]
    assert await read_body(request) == {"cached": True}  # type: ignore[arg-type]


async def test_read_body_form_urlencoded() -> None:
    request = _request(
        body=b"a=1&b=two",
        content_type="application/x-www-form-urlencoded",
    )
    assert await read_body(request) == {"a": "1", "b": "two"}  # type: ignore[arg-type]


async def test_read_body_json() -> None:
    request = _request(body=b'{"x": 1, "y": "v"}')
    assert await read_body(request) == {"x": 1, "y": "v"}  # type: ignore[arg-type]


async def test_read_body_json_empty() -> None:
    request = _request(body=b"")
    assert await read_body(request) == {}  # type: ignore[arg-type]


async def test_read_body_json_non_mapping() -> None:
    request = _request(body=b'"hello"')
    assert await read_body(request) == {}  # type: ignore[arg-type]


async def test_read_body_other_content_type() -> None:
    request = _request(body=b"binary", content_type="application/octet-stream")
    assert await read_body(request) == {}  # type: ignore[arg-type]


async def test_read_body_cached_second_call() -> None:
    request = _request(body=b'{"x": 1}')
    first = await read_body(request)  # type: ignore[arg-type]
    second = await read_body(request)  # type: ignore[arg-type]
    assert first == second == {"x": 1}


async def test_claims_cached() -> None:
    request = _request()
    request[CLAIMS] = {"cached": True}  # type: ignore[index]
    assert claims(request) == {"cached": True}  # type: ignore[arg-type]


async def test_claims_no_authorization() -> None:
    request = _request()
    assert claims(request) is None  # type: ignore[arg-type]


async def test_claims_wrong_scheme() -> None:
    request = _request(headers={"Authorization": "Basic abc"})
    assert claims(request) is None  # type: ignore[arg-type]


async def test_claims_valid_token() -> None:
    token = jwt.encode({"u": "alice"}, key="a" * 32, algorithm="HS256")
    request = _request(headers={"Authorization": f"Bearer {token}"})
    result = claims(request)  # type: ignore[arg-type]
    assert result is not None
    assert result["user_id"] == "alice"


async def test_claims_cached_after_first_call() -> None:
    token = jwt.encode({"u": "bob"}, key="a" * 32, algorithm="HS256")
    request = _request(headers={"Authorization": f"Bearer {token}"})
    first = claims(request)  # type: ignore[arg-type]
    second = claims(request)  # type: ignore[arg-type]
    assert first == second


async def test_verified_claims_no_header() -> None:
    request = _request()
    assert verified_claims(request) is None  # type: ignore[arg-type]


async def test_verified_claims_wrong_scheme() -> None:
    request = _request(headers={"Authorization": "Basic abc"})
    assert verified_claims(request) is None  # type: ignore[arg-type]


async def test_verified_claims_empty_token() -> None:
    request = _request(headers={"Authorization": "Bearer   "})
    assert verified_claims(request) is None  # type: ignore[arg-type]


async def test_verified_claims_invalid_token() -> None:
    request = _request(headers={"Authorization": "Bearer not-a-token"})
    assert verified_claims(request) is None  # type: ignore[arg-type]


async def test_verified_claims_valid_token() -> None:
    key_bytes = bumper_isc.server_key.read_bytes()
    token = jwt.encode(
        {"u": "alice", "t": "a", "exp": 9999999999},
        key=key_bytes,
        algorithm=bumper_isc.TOKEN_JWT_ALG,
    )
    request = _request(headers={"Authorization": f"Bearer {token}"})
    result = verified_claims(request)  # type: ignore[arg-type]
    assert result is not None
    assert result["user_id"] == "alice"


async def test_device_id_present() -> None:
    request = _request(match_info={"devid": "dev-1"})
    assert device_id(request) == "dev-1"  # type: ignore[arg-type]


async def test_device_id_absent() -> None:
    request = _request()
    assert device_id(request) is None  # type: ignore[arg-type]


async def test_claimed_userid_query_userid() -> None:
    request = _request(query="userid=alice")
    assert claimed_userid(request) == "alice"  # type: ignore[arg-type]


async def test_claimed_userid_query_uid() -> None:
    request = _request(query="uid=bob")
    assert claimed_userid(request) == "bob"  # type: ignore[arg-type]


async def test_claimed_userid_header() -> None:
    request = _request(headers={"userid": "carol"})
    assert claimed_userid(request) == "carol"  # type: ignore[arg-type]


async def test_claimed_userid_auth_json() -> None:
    request = _request(query=urlencode({"auth": '{"userid": 42}'}))
    assert claimed_userid(request) == "42"  # type: ignore[arg-type]


async def test_claimed_userid_auth_invalid_json() -> None:
    request = _request(query=urlencode({"auth": "{bad"}))
    assert claimed_userid(request) is None  # type: ignore[arg-type]


async def test_claimed_userid_auth_non_mapping() -> None:
    request = _request(query=urlencode({"auth": '["x"]'}))
    assert claimed_userid(request) is None  # type: ignore[arg-type]


async def test_claimed_userid_none() -> None:
    request = _request()
    assert claimed_userid(request) is None  # type: ignore[arg-type]
