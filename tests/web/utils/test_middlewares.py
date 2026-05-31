import gzip
import json
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_response import Response, StreamResponse
import pytest

from bumper.utils.settings import config as bumper_isc
from bumper.web.utils.middlewares import CustomEncoder, log_all_requests

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


@pytest.fixture(autouse=True)
def enable_debug_logging() -> None:
    bumper_isc.DEBUG_LOGGING_API_REQUEST = True
    bumper_isc.DEBUG_LOGGING_API_REQUEST_MISSING = False


@pytest.fixture
def app() -> Application:
    async def handler(_: web.Request) -> Response:
        return web.json_response({"msg": "ok"})

    test_app = Application(middlewares=[log_all_requests])
    test_app.router.add_post("/test", handler)
    test_app.router.add_post("/static", handler)  # Excluded route
    return test_app


def test_custom_encoder_handles_set() -> None:
    data = {"numbers": {1, 2, 3}}
    encoded: str = json.dumps(data, cls=CustomEncoder)
    decoded: dict[str, Any] = json.loads(encoded)
    assert isinstance(decoded["numbers"], list)
    assert sorted(decoded["numbers"]) == [1, 2, 3]


async def test_middleware_logs_json_request(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/test", json={"key": "value"})
    assert resp.status == 200
    assert await resp.json() == {"msg": "ok"}
    assert "response" in caplog.text
    assert "request" in caplog.text


async def test_middleware_skips_excluded_route(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/static", data="some data")
    assert resp.status == 200
    assert "response" not in caplog.text
    assert "request" not in caplog.text


async def test_middleware_logs_form_body(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/test", data={"foo": "bar"})
    assert resp.status == 200
    assert "foo" in caplog.text


async def test_middleware_logs_json_response(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/test", json={"hello": "world"})
    assert resp.status == 200
    assert '"msg": "ok"' in await resp.text()
    assert '"request"' in caplog.text


async def test_middleware_logs_text_response(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def text_handler(_: web.Request) -> Response:
        return web.Response(text="simple text", content_type="text/plain")

    app.router.add_post("/text", text_handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/text", data="")
    assert resp.status == 200
    assert "simple text" in await resp.text()
    assert "response" in caplog.text


async def test_middleware_logs_binary_request(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client: TestClient = await aiohttp_client(app)
    resp = await client.post(
        "/test",
        data=b"binarydata",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert resp.status == 200
    assert "request" in caplog.text


async def test_middleware_logs_compressed_response(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def gzip_handler(_: web.Request) -> Response:
        content = gzip.compress(b"compressed body")
        return web.Response(
            body=content,
            headers={"Content-Encoding": "gzip", "Content-Type": "text/plain"},
        )

    app = Application(middlewares=[log_all_requests])
    app.router.add_post("/gzip", gzip_handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/gzip", data="")
    assert resp.status == 200
    assert "sample_b64" in caplog.text
    assert "binary" in caplog.text


async def test_middleware_logs_streamed_response(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def stream_handler(_: web.Request) -> StreamResponse:
        return web.StreamResponse(status=200)

    app = Application(middlewares=[log_all_requests])
    app.router.add_post("/stream", stream_handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/stream", data="")
    assert resp.status == 200
    assert "body not available" in caplog.text


async def test_middleware_handles_invalid_json_body(
    aiohttp_client: pytest.FixtureRequest,
    app: Application,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client: TestClient = await aiohttp_client(app)
    resp = await client.post(
        "/test",
        data="not-json",
        headers={"Content-Type": "application/json"},
    )
    # assert resp.status == 500
    # assert "during logging the request/response" in caplog.text
    assert resp.status == 200
    assert "Failed to decode body as json" in caplog.text


async def test_middleware_logs_missing_route_warning(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    bumper_isc.DEBUG_LOGGING_API_REQUEST_MISSING = True

    app = Application(middlewares=[log_all_requests])

    async def handler(_: web.Request) -> Response:
        return web.json_response({"ok": True})

    app.router.add_post("/known", handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/unknown", data="test")
    # Path not found triggers 404
    assert resp.status in (404, 500)
    assert "Requested API is not implemented" in caplog.text


async def test_middleware_charset_fallback(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def bad_charset_handler(_: web.Request) -> Response:
        body = "áéíóú".encode("utf-16")  # intentionally different encoding
        return web.Response(body=body, content_type="text/plain", charset="utf-8")

    app = Application(middlewares=[log_all_requests])
    app.router.add_post("/badcharset", bad_charset_handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/badcharset", data="")
    assert resp.status == 200
    assert "using 'replace' fallback" in caplog.text


async def test_middleware_handles_none_response(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def null_handler(_: web.Request) -> None:
        return None  # This triggers the `response is None` branch

    app = web.Application(middlewares=[log_all_requests])
    app.router.add_post("/null", null_handler)
    client = await aiohttp_client(app)

    resp = await client.post("/null", data="test")
    assert resp.status == 204  # HTTPNoContent
    assert "Response was null!" in caplog.text
