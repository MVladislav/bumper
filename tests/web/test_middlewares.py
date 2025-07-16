import json
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_response import Response
import pytest

from bumper.utils.settings import config as bumper_isc
from bumper.web.middlewares import CustomEncoder, log_all_requests

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


def test_custom_encoder_handles_set() -> None:
    data = {"numbers": {1, 2, 3}}
    encoded: str = json.dumps(data, cls=CustomEncoder)
    decoded: dict[str, Any] = json.loads(encoded)
    assert isinstance(decoded["numbers"], list)
    assert sorted(decoded["numbers"]) == [1, 2, 3]


@pytest.fixture
def app() -> Application:
    async def handler(_: web.Request) -> Response:
        return web.json_response({"msg": "ok"})

    test_app = web.Application(middlewares=[log_all_requests])
    test_app.router.add_post("/test", handler)
    test_app.router.add_post("/static", handler)  # Excluded route
    return test_app


@pytest.fixture(autouse=True)
def enable_debug_logging() -> None:
    bumper_isc.DEBUG_LOGGING_API_REQUEST = True
    bumper_isc.DEBUG_LOGGING_API_REQUEST_MISSING = False


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


async def test_middleware_handles_form_body(
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


async def test_middleware_handles_unknown_request_content_type(
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


async def test_middleware_skips_if_no_route_resource(
    aiohttp_client: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def handler(_: web.Request) -> Response:
        return web.Response(text="ok")

    app = web.Application(middlewares=[log_all_requests])
    app.router.add_route("POST", "/noresource/{name:.*}", handler)

    client: TestClient = await aiohttp_client(app)
    resp = await client.post("/noresource/xyz", data="test")
    assert resp.status == 200
    assert "request" in caplog.text


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
    # request.json() should raise and be caught
    assert resp.status == 500
    assert "during logging the request" in caplog.text
