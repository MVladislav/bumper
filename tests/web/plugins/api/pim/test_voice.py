"""Tests for bumper/web/plugins/api/pim/voice.py"""

from aiohttp.test_utils import TestClient
import pytest

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins.api.pim import voice
from bumper.web.static_api import get_voices


@pytest.mark.usefixtures("clean_database")
async def test_voice_get_reads_the_language_from_the_body(webserver_client: TestClient) -> None:
    """The app sends the language in the body of the POST."""
    async with webserver_client.post(
        "/api/pim/voice/get",
        json={"voiceLang": "DE", "mid": "p95mgv", "id": "default"},
    ) as resp:
        assert resp.status == 200
        body = await resp.json()

    voices = body["voices"]
    assert len(voices) == 1
    assert voices[0]["voiceLang"] == "de"
    assert voices[0]["languageName"] == "Deutsch"


@pytest.mark.usefixtures("clean_database")
async def test_voice_get_answers_english_by_default(webserver_client: TestClient) -> None:
    """A request without a language falls back to the English voice."""
    async with webserver_client.post("/api/pim/voice/get", json={"mid": "p95mgv"}) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["voices"][0]["voiceLang"] == "en"


@pytest.mark.usefixtures("clean_database")
async def test_voice_get_carries_the_file_of_the_language(webserver_client: TestClient) -> None:
    """The answer names the file the robot downloads to install the voice."""
    async with webserver_client.post(
        "/api/pim/voice/get",
        json={"voiceLang": "DE", "mid": "p95mgv", "id": "default"},
    ) as resp:
        body = await resp.json()

    voice = body["voices"][0]
    assert voice["voiceUrl"].endswith("/api/pim/voice/download/68ad813a3c7ade7f3a576521")
    assert voice["voiceUrl"].startswith("https://")
    assert voice["voiceMd5"] == "2421435caad32a736f4444045a71da4a"
    assert voice["voiceSize"] == 5098769


@pytest.mark.usefixtures("clean_database")
async def test_voice_urls_use_the_host_the_app_uses(webserver_client: TestClient) -> None:
    """The robot downloads the file, so the URL has to reach Bumper.

    The apex domain is not covered by the `*.ecouser.net` DNS override, so a
    URL built on it would leave the network instead of reaching Bumper.
    """
    async with webserver_client.post(
        "/api/pim/voice/get",
        json={"voiceLang": "DE", "mid": "p95mgv", "id": "default"},
    ) as resp:
        body = await resp.json()

    voice = body["voices"][0]
    host = f"api-app.{bumper_isc.DOM_SUB_1}{bumper_isc.DOMAIN_MAIN}"
    assert voice["voiceUrl"] == f"https://{host}/api/pim/voice/download/68ad813a3c7ade7f3a576521"
    assert voice["iconUrl"].startswith(f"https://{host}/")
    assert voice["sampleVoiceUrl"].startswith(f"https://{host}/")


@pytest.mark.usefixtures("clean_database")
async def test_voice_get_for_an_unknown_language(webserver_client: TestClient) -> None:
    """A language without voice data has no voice."""
    async with webserver_client.post(
        "/api/pim/voice/get",
        json={"voiceLang": "XX", "mid": "p95mgv"},
    ) as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["voices"] == []


@pytest.mark.usefixtures("clean_database")
async def test_voice_get_lanuages(webserver_client: TestClient) -> None:
    """The languages the app offers a voice for."""
    async with webserver_client.get("/api/pim/v2/voice/getLanuages") as resp:
        assert resp.status == 200
        body = await resp.json()

    voices = body["voices"]
    assert len(voices) == 13
    assert {"voiceLang": "en", "languageName": "English", "support": ["yiko"]} in voices
    assert {"voiceLang": "de", "languageName": "Deutsch", "support": ["yiko"]} in voices


@pytest.mark.usefixtures("clean_database")
async def test_voice_download_without_a_file_is_404(webserver_client: TestClient) -> None:
    """Without the file the robot cannot install a voice."""
    async with webserver_client.get("/api/pim/voice/download/does_not_exist") as resp:
        assert resp.status == 404


@pytest.mark.usefixtures("clean_database")
async def test_voice_download_serves_the_file(webserver_client: TestClient) -> None:
    """The file the robot downloads is served from the voice directory."""
    voice_id = "test_voice_id"
    (bumper_isc.voice_dir / voice_id).write_bytes(b"voice-bytes")

    async with webserver_client.get(f"/api/pim/voice/download/{voice_id}") as resp:
        assert resp.status == 200
        assert await resp.read() == b"voice-bytes"

    (bumper_isc.voice_dir / voice_id).unlink()


@pytest.mark.usefixtures("clean_database")
async def test_voice_download_stays_in_the_voice_directory(webserver_client: TestClient) -> None:
    """The id comes from the request, so it cannot point at another file."""
    secret = bumper_isc.voice_dir.parent / "secret.txt"
    secret.write_text("the secret of the user")

    assert voice._voice_file("../secret.txt") is None
    assert voice._voice_file("secret.txt") is None

    async with webserver_client.get("/api/pim/voice/download/..%2Fsecret.txt") as resp:
        assert resp.status == 404

    secret.unlink()


@pytest.mark.usefixtures("clean_database")
async def test_voice_download_serves_the_file_unchanged(webserver_client: TestClient) -> None:
    """The robot checksums the bytes it receives, so they must not be encoded.

    The voice files are gzip data and the checksum in the metadata is of the
    compressed bytes. A `Content-Encoding` header would make the client
    decompress them and the checksum would no longer match.
    """
    voice_id = "test_voice_gzip"
    payload = b"\x1f\x8b\x08\x00compressed-voice-bytes"
    (bumper_isc.voice_dir / voice_id).write_bytes(payload)

    async with webserver_client.get(f"/api/pim/voice/download/{voice_id}") as resp:
        assert resp.status == 200
        assert "Content-Encoding" not in resp.headers
        assert await resp.read() == payload

    (bumper_isc.voice_dir / voice_id).unlink()


@pytest.mark.usefixtures("clean_database")
async def test_every_stored_voice_has_its_file() -> None:
    """The metadata and the voice files belong to each other.

    The files are not part of the repository, so the check only runs where they
    were downloaded.
    """
    voice_dir = bumper_isc.voice_dir
    files = [file for file in voice_dir.iterdir() if file.is_file() and file.name != ".gitkeep"]
    if not files:
        pytest.skip("the voice files are not downloaded")

    missing = [
        language
        for language, voice in get_voices().items()
        if not (voice_dir / str(voice["voiceUrl"]).rsplit("/", 1)[-1]).is_file()
    ]
    assert not missing, f"no file for: {missing}"
