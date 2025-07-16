from aiohttp.test_utils import TestClient


async def test_file_get(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/api/pim/file/get/123")
    assert resp.status == 200
    content_type = resp.headers.get("Content-Type", "")
    assert content_type.startswith("image/")
    body = await resp.read()
    assert body


async def test_api_pim_file_get(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/api/pim/api/pim/file/get/456")
    assert resp.status == 200
    content_type = resp.headers.get("Content-Type", "")
    assert content_type.startswith("image/")
    body = await resp.read()
    assert body
