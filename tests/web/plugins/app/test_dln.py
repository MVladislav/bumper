from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo, clean_log_repo
from bumper.web.utils.models import CleanLog


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_no_did(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    async with webserver_client.get("/app/dln/api/log/clean_result/list") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []
        # Verify error was logged
        assert "No DID specified" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_no_bot(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    async with webserver_client.get("/app/dln/api/log/clean_result/list?did=nonexistent&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []
        # Verify error was logged
        assert "No bots with DID" in caplog.text


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_list_wrong_company(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")

    async with webserver_client.get("/app/dln/api/log/clean_result/list?did=did_1234&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
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
    rid = "sdu9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    rid = "sdu8"
    clean_log.clean_log_id = f"{did}@{start}@{rid}"
    clean_log_repo.add_or_update(clean_log)

    async with webserver_client.get(f"/app/dln/api/log/clean_result/list?did={did}&logType=clean") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
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
    rid = "sdu9"
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
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_clean_result_del(webserver_client: TestClient) -> None:
    did = "did_1234"
    # Add some clean logs
    cid = "1699297517"
    start = 1699297517
    rid = "sdu9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"
    clean_log_repo.add_or_update(clean_log)
    rid = "sdu8"
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
