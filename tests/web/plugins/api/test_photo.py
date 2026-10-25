"""Tests for the robot camera upload workflow."""

import base64
import json
import logging
import lzma
from urllib.parse import quote

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, clean_log_repo, photo_repo

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
        "auth.res": "res1",
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
    bot_repo.add(SN, DID, "p95mgv", "res1", "eco-ng")


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_upload_accepts_post(webserver_client: TestClient) -> None:
    """The upload endpoint accepts a POST.

    A 405 would still exit 0 for the robot's curl, which then deletes the JPEG
    believing it was stored.
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
    """The app shows the map as an SVG picture, the same way the cloud shows it."""
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
        assert resp.content_type == "image/svg+xml"
        picture = await resp.read()

    assert picture.startswith(b"<svg ")


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_a_map_ignores_the_removed_png_format(webserver_client: TestClient) -> None:
    """A request that still asks for PNG gets the SVG map."""
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
    async with webserver_client.get(f"/api/photo/download?id={photo_id}&format=png") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/svg+xml"
        picture = await resp.read()

    assert picture.startswith(b"<svg ")


@pytest.mark.usefixtures("clean_database")
async def test_photo_download_unknown_id_returns_placeholder(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/photo/download?id=nope") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/svg+xml"
    async with webserver_client.get("/api/photo/download") as resp:
        assert resp.status == 200
        assert resp.content_type == "image/svg+xml"


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_photo_delete_all(webserver_client: TestClient) -> None:
    await _upload(webserver_client, _meta(ts=1000))

    async with webserver_client.delete("/api/photo/all") as resp:
        assert resp.status == 200
    assert photo_repo.list_all() == []


#: The map document, the way the app sends it in the "mapInfo" section.
MAP_DOCUMENT = {
    "mid": "1",
    "majorMap": {
        "cellHeight": 8,
        "cellWidth": 8,
        "mapCount": 1,
        "mapEncode": "7z",
        "pieceHeight": 8,
        "pieceWidth": 8,
        "pixel": 50,
        "value": "1295764014",
    },
    "minorMap": {"value": _encode_7z(bytes(64))},
    "mapTrace": {"pointCount": 0, "tid": 1792662252, "totalCount": 0, "traceStart": 0, "traceValue": ""},
}

#: The clean log of a job, the way the newer app uploads it.
CLEAN_LOG = {
    "arSet": {"infoSize": 14, "value": _encode_7z(b"synthetic path")},
    "mapInfo": {"infoSize": 9716, "value": _encode_7z(json.dumps(MAP_DOCUMENT).encode())},
    "mapTrace": MAP_DOCUMENT["mapTrace"],
    "mid": "1",
    "pos": {"chargePos": [{"a": 0, "invalid": 1, "x": 0, "y": 0}], "deebotPos": {"a": 0, "invalid": 0, "x": 100, "y": 200}},
    "stats": {
        "area": 580100,
        "end": 1792662252,
        "start": 1792580181,
        "stopReason": 1,
        "time": 2531,
        "totalArea": 580100,
        "type": "auto",
    },
    "vwSet": {"infoSize": 2, "value": _encode_7z(bytes(2))},
}


@pytest.mark.usefixtures("clean_database")
async def test_photo_download_renders_a_map_stored_in_the_upload_wrapper(webserver_client: TestClient) -> None:
    """An older stored photo can still contain the map upload wrapper."""
    map_document = {
        "majorMap": {"cellHeight": 8, "cellWidth": 8, "pieceHeight": 8, "pieceWidth": 8, "pixel": 50},
        "minorMap": {"value": _encode_7z(bytes([1]) + bytes(4095))},
    }
    wrapper = {
        "mapInfo": {"value": _encode_7z(json.dumps(map_document).encode())},
        "mapTrace": {"pointCount": 0, "tid": 1, "totalCount": 0, "traceStart": 0, "traceValue": ""},
    }
    photo_repo.add(
        {
            "id": "legacy-wrapper-map",
            "did": DID,
            "ts": 1792845283000,
            "kind": "map",
            "image": photo_repo.encode_image(json.dumps(wrapper).encode()),
        },
    )

    async with webserver_client.get("/api/photo/download?id=legacy-wrapper-map&format=svg") as resp:
        image = await resp.read()

    assert resp.status == 200
    assert resp.content_type == "image/svg+xml"
    assert image.startswith(b"<svg ")


def _clean_log_meta() -> str:
    """Return the meta of a clean log, the way the app sends it."""
    return quote(
        json.dumps(
            {
                "fw_ver": "1.11.23",
                "product": "x5_mr2337",
                "sn": SN,
                "ts": "1792662252",
            },
        ),
    )


def _clean_log_query() -> str:
    """Return the query of a clean log upload."""
    params = {
        "auth.with": "device",
        "auth.name": SN,
        "auth.did": DID,
        "auth.mid": "p95mgv",
        "auth.res": "res1",
        "auth.ts": "1792662252",
        "auth.sign": "0123456789abcdef0123456789abcdef",
        "rn": "CleanResult",
        "meta": _clean_log_meta(),
        "fmt": "j",
        "dType": "string",
    }
    return "&".join(f"{key}={value}" for key, value in params.items())


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_the_clean_log_of_a_job_is_accepted_on_the_new_path(webserver_client: TestClient) -> None:
    """The newer app posts the clean log of a job to the "idi" endpoint."""
    async with webserver_client.post(
        f"/api/idi/data_collect/upload/generalData?{_clean_log_query()}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(CLEAN_LOG),
    ) as resp:
        assert resp.status == 200


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_the_clean_log_of_a_job_is_stored(webserver_client: TestClient) -> None:
    """The clean log is stored, so the app can read the job back."""
    async with webserver_client.post(
        f"/api/idi/data_collect/upload/generalData?{_clean_log_query()}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(CLEAN_LOG),
    ) as resp:
        assert resp.status == 200

    photos = photo_repo.list_by_did(limit=10, kind="map")
    assert photos, "the map of the job was not stored"

    # The document of the map is what the app reads, so the wrapper of the
    # clean log is gone.
    document = photo_repo.decode_map(photos[0]["image"])
    assert document["majorMap"]["pieceWidth"] == 8
    assert document["minorMap"]["value"] == MAP_DOCUMENT["minorMap"]["value"]


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_the_statistics_of_the_upload_become_a_clean_log(webserver_client: TestClient) -> None:
    """The upload carries the statistics of the job, so the log list can show it."""
    async with webserver_client.post(
        f"/api/idi/data_collect/upload/generalData?{_clean_log_query()}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(CLEAN_LOG),
    ) as resp:
        assert resp.status == 200

    logs = clean_log_repo.list_by_did(DID)
    assert len(logs) == 1
    assert logs[0].ts == CLEAN_LOG["stats"]["start"]
    assert logs[0].end == CLEAN_LOG["stats"]["end"]
    assert logs[0].last == CLEAN_LOG["stats"]["time"]
    # The area is uploaded in square millimetres and shown in square metres.
    assert logs[0].area == CLEAN_LOG["stats"]["area"] // 10000
    assert logs[0].type == CLEAN_LOG["stats"]["type"]
    assert logs[0].stop_reason == CLEAN_LOG["stats"]["stopReason"]


@pytest.mark.usefixtures("clean_database", "camera_bot")
async def test_the_same_job_is_not_stored_twice(webserver_client: TestClient) -> None:
    """An upload of the same job replaces the record instead of adding one."""
    for _ in range(2):
        async with webserver_client.post(
            f"/api/idi/data_collect/upload/generalData?{_clean_log_query()}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(CLEAN_LOG),
        ) as resp:
            assert resp.status == 200

    assert len(clean_log_repo.list_by_did(DID)) == 1
