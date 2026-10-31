import asyncio
from pathlib import Path

from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request
import pytest
from yarl import URL

from bumper.utils.settings import config as bumper_isc
from bumper.web.server import WEB_SHUTDOWN_TIMEOUT, WebServer, WebserverBinding
from tests import HOST, WEBSERVER_PORT


async def test_webserver_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, True), False)
    await server.start()
    await server.shutdown()


async def test_webserver_no_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 1, False), False)
    await server.start()
    await server.shutdown()


async def test_webserver_shutdown_timeout_is_bounded() -> None:
    """Do not retain HTTP handlers past the Ecovacs client's request deadline."""
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 1, False), False)
    await server.start()
    try:
        assert server._runner is not None
        assert server._runner._shutdown_timeout == WEB_SHUTDOWN_TIMEOUT
    finally:
        await server.shutdown()


async def test_multiple_web_bindings_share_one_runner() -> None:
    """Bind TLS and cleartext sites under one app lifecycle runner."""
    server = WebServer(
        [
            WebserverBinding(HOST, WEBSERVER_PORT + 9, False),
            WebserverBinding(HOST, WEBSERVER_PORT + 10, False),
        ],
        False,
    )
    await server.start()
    try:
        assert server.started
        assert server._runner is not None
        assert len(server._runner.sites) == 2
    finally:
        await server.shutdown()
    assert not server.started
    assert server._runner is None


@pytest.mark.usefixtures("clean_database", "xmpp_server", "helper_bot")
async def test_base(webserver_client: TestClient) -> None:
    async with webserver_client.get("/") as resp:
        assert resp.status == 200


async def test_webserver_log_voice_files_oserror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    voice_file = tmp_path / "voice_file"
    voice_file.write_text("x")
    monkeypatch.setattr(bumper_isc, "voice_dir", voice_file)
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 2, False), False)
    await server.start()
    await server.shutdown()


async def test_webserver_log_voice_files_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir()
    (voice_dir / "v.wav").write_text("x")
    monkeypatch.setattr(bumper_isc, "voice_dir", voice_dir)
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 3, False), False)
    await server.start()
    await server.shutdown()


async def test_webserver_shutdown_exception() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 4, False), False)
    await server.start()

    async def boom() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    server._app.shutdown = boom  # type: ignore[assignment]
    with pytest.raises(RuntimeError):
        await server.shutdown()


async def test_proxy_special_paths() -> None:
    proxy_server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 5, False), True)
    proxy_ts = TestServer(proxy_server._app)
    await proxy_ts.start_server()
    try:
        async with ClientSession() as session:
            async with session.get(proxy_ts.make_url("/")) as resp:
                assert resp.status in (200, 500)
            async with session.post(proxy_ts.make_url("/lookup.do")) as resp:
                assert resp.status in (200, 404, 500)
    finally:
        await proxy_ts.close()


async def test_proxy_outbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def upstream_handler(request: web.Request) -> web.Response:
        if request.path == "/binary":
            return web.Response(body=b"binary-data", content_type="application/octet-stream")
        body = b""
        if request.content_length:
            body = await request.read()
        text = "ok"
        if body:
            text = text + " " + body.decode("utf-8", errors="replace")
        return web.Response(text=text)

    upstream_app = web.Application()
    upstream_app.router.add_route("*", "/{path:.*}", upstream_handler)
    upstream_ts = TestServer(upstream_app)
    await upstream_ts.start_server()

    proxy_server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 6, False), True)
    proxy_ts = TestServer(proxy_server._app)
    await proxy_ts.start_server()

    def fake_validate(url: URL) -> str:
        return str(upstream_ts.make_url(url.raw_path))

    monkeypatch.setattr(proxy_server, "_validate_and_sanitize_url", fake_validate)
    try:
        async with ClientSession() as session:
            async with session.get(proxy_ts.make_url("/hello")) as resp:
                assert resp.status == 200
            async with session.get(proxy_ts.make_url("/binary")) as resp:
                assert resp.status == 200
                assert await resp.read() == b"binary-data"
            async with session.post(proxy_ts.make_url("/form"), data={"a": "b"}) as resp:
                assert resp.status == 200
            async with session.post(proxy_ts.make_url("/json"), json={"a": 1}) as resp:
                assert resp.status == 200
    finally:
        await proxy_ts.close()
        await upstream_ts.close()


async def test_proxy_invalid_host() -> None:
    proxy_server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 7, False), True)
    proxy_ts = TestServer(proxy_server._app)
    await proxy_ts.start_server()
    try:
        async with ClientSession() as session, session.get(proxy_ts.make_url("/hello")) as resp:
            assert resp.status == 500
    finally:
        await proxy_ts.close()


async def test_proxy_cancelled() -> None:
    proxy_server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 8, False), True)

    request = make_mocked_request("GET", "/hello", app=proxy_server._app, match_info={})

    def fake_validate_cancel(url: URL) -> str:
        _ = url
        raise asyncio.CancelledError

    proxy_server._validate_and_sanitize_url = fake_validate_cancel  # type: ignore[assignment]
    with pytest.raises(asyncio.CancelledError):
        await proxy_server._handle_proxy(request)


def test_validate_and_sanitize_url_allowed() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, False), False)
    url = URL("http://ecouser.net/path?q=1#frag")
    result = server._validate_and_sanitize_url(url)
    assert result == "http://ecouser.net/path"


def test_validate_and_sanitize_url_allowed_ecovacs() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, False), False)
    url = URL("http://ecovacs.com/path")
    result = server._validate_and_sanitize_url(url)
    assert result == "http://ecovacs.com/path"


def test_validate_and_sanitize_url_disallowed() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, False), False)
    url = URL("http://evil.com/path")
    with pytest.raises(ValueError, match="Invalid or unauthorized host"):
        server._validate_and_sanitize_url(url)
