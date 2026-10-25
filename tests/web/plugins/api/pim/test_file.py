from aiohttp.test_utils import TestClient


async def test_file_get(webserver_client: TestClient) -> None:
    """Both file paths used by app versions return the bot image."""
    for path in ("/api/pim/file/get/123", "/api/pim/api/pim/file/get/123"):
        async with webserver_client.get(path) as resp:
            assert resp.status == 200
            content_type = resp.headers.get("Content-Type", "")
            assert content_type.startswith("image/")
            assert await resp.read()
