from aiohttp.test_utils import TestClient


async def test_voice_get(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/pim/voice/get?voiceLang=en") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 0
        assert "voices" in data
        assert isinstance(data["voices"], list)


async def test_voice_get_lanuages(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/pim/voice/getLanuages") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 0
        assert "voices" in data
        assert isinstance(data["voices"], list)


async def test_voice_v2_get_lanuages(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/pim/v2/voice/getLanuages") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 0
        assert "voices" in data
        assert isinstance(data["voices"], list)


async def test_voice_download(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/pim/voice/download/123") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 0
        # assert "voices" in data
