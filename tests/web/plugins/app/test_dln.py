import json
from pathlib import Path

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, clean_log_repo, photo_repo
from bumper.db.photos import KIND_MAP
from bumper.web.utils.models import CleanLog


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_no_did(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    async with webserver_client.get("/app/dln/api/log/clean_result/list") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert json_resp["message"] == "success"
        assert json_resp["data"] == []
        # Verify error was logged
        assert "No DID specified" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_no_bot(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    async with webserver_client.get("/app/dln/api/log/clean_result/list?did=nonexistent&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert json_resp["message"] == "success"
        assert json_resp["data"] == []
        # Verify error was logged
        assert "No bots with DID" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_wrong_company(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")

    async with webserver_client.get("/app/dln/api/log/clean_result/list?did=did_1234&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert json_resp["message"] == "success"
        assert json_resp["data"] == []
        # Verify error was logged
        assert "No bots with DID" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_with_logs(webserver_client: TestClient) -> None:
    # Add a bot with the correct company
    did = "did_1234"
    bot_repo.add("sn_1234", did, "class_1234", "res_1234", "eco-ng")

    # Add some clean logs
    cid = "1699297517"
    start = 1699297517
    rid = "res9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    rid = "res8"
    clean_log.clean_log_id = f"{did}@{start}@{rid}"
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert json_resp["message"] == "success"
        assert len(json_resp["data"]) == 2
        # Verify logs are sorted by timestamp in descending order
        assert json_resp["data"][0]["ts"] >= json_resp["data"][1]["ts"]
        # Verify all logs have the did field
        for log in json_resp["data"]:
            assert log["did"] == did


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_non_clean_type(webserver_client: TestClient) -> None:
    # Add a bot with the correct company
    did = "did_1234"
    bot_repo.add("sn_1234", did, "class_1234", "res_1234", "eco-ng")

    # Add a clean log (should be ignored if logType is not "clean")
    cid = "1699297517"
    start = 1699297517
    rid = "res9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=other") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert json_resp["message"] == "success"
        assert json_resp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_del(webserver_client: TestClient) -> None:
    did = "did_1234"
    # Add some clean logs
    cid = "1699297517"
    start = 1699297517
    rid = "res9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    rid = "res8"
    clean_log.clean_log_id = f"{did}@{start}@{rid}"
    clean_log_repo.add_or_update(clean_log)

    # Verify logs exist
    clean_log_list = clean_log_repo.list_all()
    assert len(clean_log_list) == 2

    log_id_list = []
    for c in clean_log_list:
        assert clean_log_repo.list_by_id(c.clean_log_id) is not None
        log_id_list.append(c.clean_log_id)

    # Delete the logs
    async with webserver_client.post("/app/dln/api/log/clean_result/del", json={"logIds": log_id_list}) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp.get("data") is None

    # Verify logs are deleted
    for log_id in log_id_list:
        assert clean_log_repo.list_by_id(log_id) is None


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_del_empty_list(webserver_client: TestClient) -> None:
    async with webserver_client.post("/app/dln/api/log/clean_result/del", json={"logIds": []}) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp.get("data") is None


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_del_no_log_ids(webserver_client: TestClient) -> None:
    async with webserver_client.post("/app/dln/api/log/clean_result/del", json={}) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp.get("data") is None


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_del_nonexistent_ids(webserver_client: TestClient) -> None:
    async with webserver_client.post(
        "/app/dln/api/log/clean_result/del",
        json={"logIds": ["nonexistent1", "nonexistent2"]},
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp.get("data") is None


def _clean_log(did: str, start: int, end: int | None = None) -> CleanLog:
    """Return a clean log of a robot."""
    clean_log = CleanLog(f"{did}@{start}@res9")
    clean_log.did = did
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log.area = 28
    clean_log.last = 600
    clean_log.end = end
    return clean_log


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_list_works_without_a_log_type(webserver_client: TestClient) -> None:
    """The newer app leaves the type of the log out."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "p95mgv", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&res=res1&size=10") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["code"] == 0
    assert len(json_resp["data"]) == 1
    assert json_resp["data"][0]["id"] == f"{did}@1699297517@res9"
    assert json_resp["data"][0]["ts"] == 1699297517


@pytest.mark.usefixtures("clean_database")
async def test_a_job_without_a_map_points_at_the_placeholder(webserver_client: TestClient) -> None:
    """A job without a stored map still carries a download URL for the app."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "300lc5", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=clean") as resp:
        json_resp = await resp.json()

    assert "/api/photo/download?format=svg" in json_resp["data"][0]["imageUrl"]
    assert "id=" not in json_resp["data"][0]["imageUrl"]


@pytest.mark.usefixtures("clean_database")
async def test_the_map_url_is_the_svg_picture(webserver_client: TestClient) -> None:
    """The app receives the SVG form of the map."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "300lc5", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))
    photo_repo.add({"id": "photo_1", "did": did, "ts": 1699297517, "kind": KIND_MAP, "image": ""})

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=clean") as resp:
        json_resp = await resp.json()
    assert json_resp["data"][0]["imageUrl"].endswith("&format=svg")


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_list_accepts_the_serial_number(webserver_client: TestClient) -> None:
    """Some robots are asked for by serial number instead of device ID."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "300lc5", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))

    async with webserver_client.get("/app/dln/api/log/clean_result/list?did=sn_1234&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["code"] == 0
    assert len(json_resp["data"]) == 1
    assert json_resp["data"][0]["did"] == "sn_1234"


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_list_honours_the_size(webserver_client: TestClient) -> None:
    """The app asks for a number of jobs."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "p95mgv", "res1", "eco-ng")
    for start in (1699297517, 1699297518, 1699297519):
        clean_log_repo.add_or_update(_clean_log(did, start))

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&size=2") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert len(json_resp["data"]) == 2


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_list_pages_backwards(webserver_client: TestClient) -> None:
    """The app pages backwards through the jobs."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "p95mgv", "res1", "eco-ng")
    for start in (1699297517, 1699297518, 1699297519):
        clean_log_repo.add_or_update(_clean_log(did, start))

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&before=1699297519") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert [entry["ts"] for entry in json_resp["data"]] == [1699297518, 1699297517]


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_list_shows_the_map_of_a_job(webserver_client: TestClient) -> None:
    """The picture of a job is the map the robot uploaded."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "p95mgv", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))
    photo_repo.add(
        {
            "id": "1699297817000did_1234",
            "did": did,
            "ts": 1699297817,
            "size": 10,
            "type": "robot",
            "mtype": "pic",
            "kind": "map",
            "image": photo_repo.encode_image(b"{}"),
        },
    )

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["data"][0]["imageUrl"].endswith("/api/photo/download?id=1699297817000did_1234&format=svg")


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_data_returns_the_saved_map_for_a_log(webserver_client: TestClient) -> None:
    """The clean-result data URL resolves a job id to its stored map."""
    did = "did_1234"
    start = 1792840184
    end = 1792845283
    clean_log = _clean_log(did, start)
    bot_repo.add("sn_1234", did, "300lc5", "res1", "eco-ng")
    clean_log_repo.add_or_update(clean_log)
    map_document = json.loads((Path(__file__).parents[3] / "utils/stored_map.json").read_text())
    photo_repo.add(
        {
            "id": f"{end * 1000}{did}",
            "did": did,
            "ts": end,
            "kind": KIND_MAP,
            "image": photo_repo.encode_image(json.dumps(map_document).encode()),
        },
    )

    async with webserver_client.get(
        "/app/dln/api/log/clean_result/data",
        params={"id": clean_log.clean_log_id, "channel": "google_play"},
    ) as resp:
        image = await resp.read()

    assert resp.status == 200
    assert resp.content_type == "image/svg+xml"
    assert image.startswith(b"<svg ")


@pytest.mark.usefixtures("clean_database")
async def test_the_clean_result_data_returns_not_found_without_a_map(webserver_client: TestClient) -> None:
    """A clean result without a stored map has no data file to return."""
    clean_log = _clean_log("did_1234", 1792840184, 1792845283)
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get(
        "/app/dln/api/log/clean_result/data",
        params={"id": clean_log.clean_log_id},
    ) as resp:
        body = await resp.read()

    assert resp.status == 404
    assert body == b""


@pytest.mark.usefixtures("clean_database")
async def test_the_patrol_logs_are_not_shown(webserver_client: TestClient) -> None:
    """The patrol runs are a kind of log of their own."""
    did = "did_1234"
    bot_repo.add("sn_1234", did, "p95mgv", "res1", "eco-ng")
    clean_log_repo.add_or_update(_clean_log(did, 1699297517))

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=patrol") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    assert json_resp["data"] == []
