"""The agreement page of the app."""

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_the_agreement_is_a_whole_document(webserver_client: TestClient) -> None:
    """The web view of the app expects a document, not a piece of one."""
    async with webserver_client.get("/content/agreement?id=abc&language=EN") as resp:
        assert resp.status == 200
        assert resp.content_type == "text/html"
        assert resp.charset.lower() == "utf-8"

        body = await resp.text()

    assert body.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in body
    assert '<meta charset="utf-8">' in body
    assert 'name="viewport"' in body
    assert "<body>" in body
    assert "</html>" in body


@pytest.mark.usefixtures("clean_database")
async def test_the_agreement_is_not_cached(webserver_client: TestClient) -> None:
    """The API sends the page with the headers that keep it fresh."""
    async with webserver_client.get("/content/agreement?id=abc&language=EN") as resp:
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["pragma"] == "no-cache"
        assert resp.headers["content-language"] == "en"
