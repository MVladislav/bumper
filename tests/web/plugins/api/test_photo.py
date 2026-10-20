"""Tests for the robot camera upload workflow."""

import base64
import json
import logging
import lzma
from urllib.parse import quote

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, photo_repo

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 16 + b"\xff\xd9"
DID = "did_cam"
SN = "sn_cam"


def _encode_7z(payload: bytes) -> str:
    """Encode a payload the way the robot does."""
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE)
    # The robot writes the size with four bytes instead of eight.
    short = compressed[:5] + len(payload).to_bytes(4, "little") + compressed[13:]
    return base64.b64encode(short).decode("ascii")


def _query(meta: str, **overrides: str) -> str:
    """Build the query string exactly as process_picture.sh does."""
    params = {
        "auth.with": "device",
        "auth.name": SN,
        "auth.did": DID,
        "auth.mid": "p95mgv",
        "auth.res": "rljY",
        "auth.ts": "1746022105",
        "auth.sign": "0123456789abcdef0123456789abcdef",
        "rn": "cruiseJPEG",
        "meta": quote(meta),
        "fmt": "b",
        "dType": "bin",
        **overrides,
    }
    return "&".join(f"{key}={value}" for key, value in params.items())


def _meta(bind_evt: str = "cruise", ts: int = 1746022105000, bind_id: str = "w1") -> str:
    """Return a URL-encoded meta parameter."""
    payload = json.dumps({"filename": "a.jpg", "size": len(JPEG), "bindEvt": bind_evt, "bindID": bind_id, "ts": ts})
    return quote(payload)


async def _upload(webserver_client: TestClient, meta: str, **overrides: str) -> None:
    """POST one image the way the device does."""
    async with webserver_client.post(
        f"/data_collect/upload/generalData?{_query(meta, **overrides)}",
        headers={"Content-Type": "application/octet-stream"},
        data=JPEG,
    ) as resp:
        assert resp.status == 200


@pytest.fixture
def camera_bot() -> None:
    """Register the bot the camera uploads belong to."""
    bot_repo.add(SN, DID, "p95mgv", "rljY", "eco-ng")


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_upload_accepts_post(webserver_client: TestClient) -> None:
    """The device POSTs. This used to be a GET-only route answering 405.

    curl passes no `--fail`, so a 405 still exits 0 and the robot deletes the
    JPEG believing it succeeded.
    """
    await _upload(webserver_client, _meta())


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_upload_is_stored(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta())

    stored = photo_repo.list_by_did(DID)
    assert len(stored) == 1
    assert stored[0]["bindEvt"] == "cruise"
    assert stored[0]["bindID"] == "w1"
    assert stored[0]["ts"] == 1746022105000
    assert stored[0]["size"] == len(JPEG)
    # The raw bytes must survive the round trip, not just a placeholder.
    assert photo_repo.decode_image(stored[0]["image"]) == JPEG


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_find_pet_upload(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(bind_evt="findPet", bind_id="w2"))
    assert photo_repo.list_by_did(DID)[0]["bindEvt"] == "findPet"


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_upload_without_meta_is_still_accepted(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """A malformed `meta` must not lose the image or produce a 500."""
    with caplog.at_level(logging.WARNING):
        await _upload(webserver_client, quote("not json at all"))

    assert "not valid URL-encoded JSON" in caplog.text
    # ts falls back to auth.ts, converted from seconds to milliseconds
    assert photo_repo.list_by_did(DID)[0]["ts"] == 1746022105000


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_identity_mismatch_is_logged_but_accepted(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Rejecting would break a working robot; the signature cannot be checked."""
    with caplog.at_level(logging.WARNING):
        await _upload(webserver_client, _meta(), **{"auth.res": "WRONG"})

    assert "identity mismatch" in caplog.text
    assert len(photo_repo.list_by_did(DID)) == 1


@pytest.mark.usefixtures("clean_database")
async def test_upload_for_unknown_bot_is_logged(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        await _upload(webserver_client, _meta(), **{"auth.did": "nobody"})

    assert "unknown bot" in caplog.text


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_list_returns_stored_photos(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(ts=1746022105000, bind_id="w0"))
    await _upload(webserver_client, _meta(ts=1746022106000, bind_id="w1"))

    async with webserver_client.get(f"/api/photo/list?did={DID}&limit=50") as resp:
        assert resp.status == 200
        body = await resp.json()

    assert body["code"] == 0
    data = body["data"]
    assert len(data) == 2
    # Newest first.
    assert data[0]["ts"] == 1746022106000
    assert data[0]["type"] == "robot"
    assert data[0]["mtype"] == "pic"
    assert data[0]["did"] == DID


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_list_paging(webserver_client: TestClient) -> None:
    for ts in (1000, 2000, 3000):
        await _upload(webserver_client, _meta(ts=ts))

    async with webserver_client.get(f"/api/photo/list?did={DID}&before=3000") as resp:
        data = (await resp.json())["data"]
    assert [entry["ts"] for entry in data] == [2000, 1000]


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_list_filters_on_type(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(ts=1000))

    # Everything the device uploads is `type=robot`; a `user` filter must be empty.
    async with webserver_client.get(f"/api/photo/list?did={DID}&type=user") as resp:
        assert (await resp.json())["data"] == []
    async with webserver_client.get(f"/api/photo/list?did={DID}&type=robot") as resp:
        assert len((await resp.json())["data"]) == 1


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_list_without_did_covers_every_robot(webserver_client: TestClient) -> None:
    """An install with several robots lists the photos of all of them."""
    await _upload(webserver_client, _meta(ts=1000))
    other = photo_repo.list_by_did(DID)[0]
    photo_repo.add({**other, "id": "other", "did": "did_other"})

    async with webserver_client.get("/api/photo/list?limit=50") as resp:
        data = (await resp.json())["data"]

    assert {entry["did"] for entry in data} == {DID, "did_other"}


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_map_upload_is_marked_as_a_map(webserver_client: TestClient) -> None:
    """A JSON payload is a map, not a picture, but both are listed as photos."""
    payload = json.dumps({"majorMap": {"mapCount": 3}, "mapTrace": {"pointCount": 9}}).encode()
    async with webserver_client.post(
        f"/data_collect/upload/generalData?{_query(_meta())}",
        headers={"Content-Type": "application/octet-stream"},
        data=payload,
    ) as resp:
        assert resp.status == 200

    stored = photo_repo.list_by_did(DID)
    assert len(stored) == 1
    assert stored[0]["kind"] == "map"
    # The app lists both kinds as pictures.
    assert stored[0]["mtype"] == "pic"
    assert photo_repo.decode_map(str(stored[0]["image"]))["majorMap"] == {"mapCount": 3}


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_download_round_trip(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(ts=1000))

    photo_id = photo_repo.list_by_did(DID)[0]["id"]
    async with webserver_client.get(f"/api/photo/download?id={photo_id}") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/jpeg"
        assert await resp.read() == JPEG


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_the_time_of_a_map_is_scaled_up(webserver_client: TestClient) -> None:
    """The robot sends the time of a map in seconds, the app wants milliseconds."""
    payload = json.dumps({"majorMap": {"mapCount": 3}, "mapTrace": {"pointCount": 9}}).encode()
    async with webserver_client.post(
        f"/data_collect/upload/generalData?{_query(_meta(ts=1792439780))}",
        headers={"Content-Type": "application/octet-stream"},
        data=payload,
    ) as resp:
        assert resp.status == 200

    stored = photo_repo.list_by_did(DID)
    assert stored[0]["ts"] == 1792439780000


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_a_map_is_served_as_a_picture(webserver_client: TestClient) -> None:
    """The app shows the map as a picture, the same way the cloud shows it."""
    # The map is 8 x 8 pieces of 8 x 8 cells, with a wall in the middle.
    grid = bytearray(64 * 64)
    grid[32 * 64 + 32] = 4
    payload = json.dumps(
        {
            "majorMap": {"cellHeight": 8, "cellWidth": 8, "pieceHeight": 8, "pieceWidth": 8, "pixel": 50},
            "minorMap": {"value": _encode_7z(bytes(grid))},
        },
    ).encode()
    async with webserver_client.post(
        f"/data_collect/upload/generalData?{_query(_meta())}",
        headers={"Content-Type": "application/octet-stream"},
        data=payload,
    ) as resp:
        assert resp.status == 200

    photo_id = photo_repo.list_by_did(DID)[0]["id"]
    async with webserver_client.get(f"/api/photo/download?id={photo_id}") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/png"
        picture = await resp.read()

    assert picture.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.usefixtures("clean_database")
async def test_photo_download_unknown_id_404(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/photo/download?id=nope") as resp:
        assert resp.status == 404
    async with webserver_client.get("/api/photo/download") as resp:
        assert resp.status == 404


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_delete_all(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(ts=1000))

    async with webserver_client.delete("/api/photo/all") as resp:
        assert resp.status == 200
    assert photo_repo.list_all() == []
