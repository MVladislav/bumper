import base64
import gzip
import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.utils.settings import config as bumper_isc


async def test_newauth_unknown_todo(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/newauth.do", json={"todo": "UnknownAction"})
    assert resp.status == 200
    data = await resp.json()
    assert data["errno"] == "1202"


async def test_lookup_eco_msg_new(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/lookup.do", json={"todo": "FindBest", "service": "EcoMsgNew"})
    assert resp.status == 200
    text = await resp.text()
    assert '"result":"ok"' in text


async def test_lookup_eco_update(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/lookup.do", json={"todo": "FindBest", "service": "EcoUpdate"})
    assert resp.status == 200
    data = await resp.json()
    assert data["result"] == "ok"
    assert "ip" in data
    assert "port" in data


async def test_android_conf(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/config/Android.conf")
    assert resp.status == 200
    data = await resp.json()
    assert data["v"] == "v1"


async def test_data_collect(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/data_collect/upload/generalData")
    assert resp.status == 200


async def test_sa_endpoint_empty_payload(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/sa", json={})
    assert resp.status == 200


async def test_sa_with_gzipped_base64_data(webserver_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    bumper_isc.DEBUG_LOGGING_SA_RESULT = True

    original_dict = {"temperature": "hot", "humidity": "high"}
    original_data = json.dumps(original_dict).encode("utf-8")
    gzipped_data = gzip.compress(original_data)
    encoded_data = base64.b64encode(gzipped_data).decode("utf-8")

    payload = {
        "gzip": "1",
        "data_list": encoded_data,
    }

    resp = await webserver_client.post(
        "/sa",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status == 200
    assert json.dumps(original_dict) in caplog.text


async def test_codepush_report_status(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/v0.1/public/codepush/report_status/deploy")
    assert resp.status == 200
    data = await resp.json()
    assert "msg" in data


async def test_codepush_update_check_default(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/v0.1/public/codepush/update_check")
    assert resp.status == 200
    data = await resp.json()
    assert "update_info" in data


async def test_codepush_update_check_with_key(webserver_client: TestClient) -> None:
    resp = await webserver_client.get(
        "/v0.1/public/codepush/update_check?deployment_key=RSYAx668chaf0tpKvf1kJNaVJmDzi4g83wsg78",  # gitleaks:allow
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["update_info"]["is_available"] is True


async def test_global_app_bury_point(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/Global_APP_BuryPoint/api")
    assert resp.status == 200
    data = await resp.json()
    assert data["header"]["result_code"] == "000000"


async def test_chat_bot_id_config(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/biz-app-config/api/v2/chat_bot_id/config")
    assert resp.status == 200
    data = await resp.json()
    assert data["data"]["chat_bot_id"] == "yiko_full_stack_en"


async def test_content_agreement(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/content/agreement")
    assert resp.status == 200
    text = await resp.text()
    assert "Welcome to Bumper" in text
