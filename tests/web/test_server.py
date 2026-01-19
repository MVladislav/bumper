from aiohttp.test_utils import TestClient
import pytest

from bumper.web.server import WebServer, WebserverBinding
from tests import HOST, WEBSERVER_PORT


async def test_webserver_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT, True), False)
    await server.start()
    await server.shutdown()
    # await asyncio.sleep(0.1)


async def test_webserver_no_ssl() -> None:
    server = WebServer(WebserverBinding(HOST, WEBSERVER_PORT + 1, False), False)
    await server.start()
    await server.shutdown()
    # await asyncio.sleep(0.1)


@pytest.mark.usefixtures("clean_database", "xmpp_server", "helper_bot")
async def test_base(webserver_client: TestClient) -> None:
    async with webserver_client.get("/") as resp:
        assert resp.status == 200
