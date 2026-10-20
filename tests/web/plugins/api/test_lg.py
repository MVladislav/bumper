import base64
import json
import lzma

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, clean_log_repo, photo_repo
from bumper.utils import map_doc
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid
from bumper.web.utils.models import CleanLog

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


def _encode_7z(payload: bytes) -> str:
    """Encode a payload the way the robot does."""
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE)
    # The robot writes the size with four bytes instead of eight.
    short = compressed[:5] + len(payload).to_bytes(4, "little") + compressed[13:]
    return base64.b64encode(short).decode("ascii")


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_logs(webserver_client: TestClient) -> None:
    test_did = "did_1234"
    bot_repo.add("sn_1234", test_did, "ls1ok3", "res_1234", "eco-ng")
    bot_repo.set_mqtt(test_did, True)

    # Test GetGlobalDeviceList
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "ECOGLOBLEac5ae987",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "did": test_did,
        "resource": "res_1234",
        "td": "GetCleanLogs",
    }
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert len(json_resp["logs"]) == 0


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_logs_show_the_map_of_a_job(webserver_client: TestClient) -> None:
    """The app shows the picture of a job from the url in the entry."""
    test_did = "did_1234"
    bot_repo.add("sn_1234", test_did, "ls1ok3", "res_1234", "eco-ng")
    start = 1699297517
    clean_log = CleanLog(f"{test_did}@{start}@sdu9")
    clean_log.did = test_did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    photo_repo.add(
        {
            "id": "1699297817000did_1234",
            "did": test_did,
            # The map was uploaded after the job started.
            "ts": 1699297817,
            "size": 10,
            "type": "robot",
            "mtype": "pic",
            "kind": "map",
            "image": photo_repo.encode_image(b"{}"),
        },
    )

    postbody = {"did": test_did, "resource": "res_1234", "td": "GetCleanLogs"}
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["ret"] == "ok"
    assert len(json_resp["logs"]) == 1
    # The app loads the picture on its own, so the url has to point at the
    # server the app is talking to.
    assert json_resp["logs"][0]["imageUrl"].endswith("/api/photo/download?id=1699297817000did_1234")


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_get_cleaned_map_is_not_the_clean_logs_document(webserver_client: TestClient) -> None:
    """GetCleanedMap must not be answered with the GetCleanLogs shape.

    The app requests a cleaned map with this `td`. Falling
    through to the generic handler returns `logs`, which is the wrong document,
    so the screen gets a well-formed 200 it cannot interpret.
    """
    postbody = {"did": "did_1234", "td": "GetCleanedMap", "k": "map", "ets": []}
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert "logs" not in json_resp
        assert json_resp["map"] == {}
        assert json_resp["trace"] == {}


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_get_cleaned_map_returns_the_stored_map(webserver_client: TestClient) -> None:
    """A stored map comes back as the pieces the app puts back together."""
    grid = bytes(range(256)) * 16
    map_document = {
        "mid": "123",
        "majorMap": {"cellHeight": 8, "cellWidth": 8, "pieceHeight": 8, "pieceWidth": 8, "pixel": 50, "value": "1,2"},
        "minorMap": {"value": _encode_7z(grid)},
        "mapTrace": {"pointCount": 7, "tid": 9},
    }
    photo_repo.add(
        {
            "id": "1000did_1234",
            "did": "did_1234",
            "ts": 1000,
            "size": 10,
            "type": "robot",
            "mtype": "pic",
            "kind": "map",
            "image": photo_repo.encode_image(json.dumps(map_document).encode()),
        },
    )

    postbody = {"did": "did_1234", "td": "GetCleanedMap", "k": "map", "ets": 2000}
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["ret"] == "ok"
    # The app reads the pieces of the map from the top level of the answer.
    assert len(json_resp["map"]) == 64
    first = map_doc.decode_7z(base64.b64decode(json_resp["map"]["0"]))
    assert len(first) == 64
    assert json_resp["trace"] == {}


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_get_cleaned_map_without_a_map(webserver_client: TestClient) -> None:
    """A device without a map has no pieces."""
    postbody = {"did": "did_1234", "td": "GetCleanedMap", "k": "map", "ets": 2000}
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["ret"] == "ok"
    assert json_resp["map"] == {}
    assert json_resp["trace"] == {}
