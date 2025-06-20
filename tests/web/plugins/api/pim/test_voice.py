async def test_voice_get(webserver_client) -> None:
    resp = await webserver_client.get("/api/pim/voice/get?voiceLang=en")
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 0
    assert "voices" in data
    assert isinstance(data["voices"], list)


async def test_voice_getLanuages(webserver_client) -> None:
    resp = await webserver_client.get("/api/pim/voice/getLanuages")
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 0
    assert "voices" in data
    assert isinstance(data["voices"], list)


async def test_voice_v2_getLanuages(webserver_client) -> None:
    resp = await webserver_client.get("/api/pim/v2/voice/getLanuages")
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 0
    assert "voices" in data
    assert isinstance(data["voices"], list)


async def test_voice_download(webserver_client) -> None:
    resp = await webserver_client.get("/api/pim/voice/download/123")
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 0
    # assert "voices" in data
