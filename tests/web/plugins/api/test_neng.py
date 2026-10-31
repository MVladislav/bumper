"""Tests for bumper/web/plugins/api/neng.py."""

from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json, post_json


@pytest.mark.usefixtures("clean_database")
async def test_neng_has_unread_message(webserver_client: TestClient) -> None:
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "ecoglobe",
            "token": "us_token",
            "userid": "user123",
            "with": "users",
        },
        "count": 20,
    }
    status, body = await post_json(webserver_client, "/api/neng/message/hasUnreadMsg", json=postbody)
    assert status == 200
    assert body["code"] == 0


@pytest.mark.usefixtures("clean_database")
async def test_neng_get_share_msgs(webserver_client: TestClient) -> None:
    status, body = await post_json(webserver_client, "/api/neng/message/getShareMsgs", json={})
    assert status == 200
    assert body["code"] == 0
    assert body["data"]["hasNext"] is False
    assert body["data"]["msgs"] == []


@pytest.mark.usefixtures("clean_database")
async def test_neng_get_list(webserver_client: TestClient) -> None:
    status, body = await post_json(webserver_client, "/api/neng/message/getlist", json={})
    assert status == 200
    assert body["code"] == 0
    assert body["data"]["hasNext"] is False
    assert body["data"]["msgs"] == []


@pytest.mark.usefixtures("clean_database")
async def test_neng_read(webserver_client: TestClient) -> None:
    status, body = await post_json(webserver_client, "/api/neng/message/read", json={})
    assert status == 200
    assert body["code"] == 0
    assert body["message"] == "success"


@pytest.mark.usefixtures("clean_database")
async def test_neng_v2_message_push(webserver_client: TestClient) -> None:
    status, body = await post_json(webserver_client, "/api/neng/v2/message/push", json={})
    assert status == 200
    assert body["code"] == 0
    assert body["message"] == ""
    assert body["data"] == "success"


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_push_status(webserver_client: TestClient) -> None:
    status, body = await get_json(
        webserver_client,
        "/api/neng/v3/message/pushStatus",
        headers={"userid": "u1"},
    )
    assert status == 200
    assert body["code"] == 0
    assert body["data"]["msgPushStatus"] == {"DEVICE": True, "SHARE": True}
    assert body["data"]["uid"] == "u1"


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_latest_by_did(webserver_client: TestClient) -> None:
    status, body = await get_json(webserver_client, "/api/neng/v3/message/latest_by_did")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_message_list(webserver_client: TestClient) -> None:
    status, body = await get_json(webserver_client, "/api/neng/v3/message/list")
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_product_msg_tabs(webserver_client: TestClient) -> None:
    status, body = await get_json(webserver_client, "/api/neng/v3/product/msg/tabs")
    assert status == 200
    assert body["code"] == 0
    assert len(body["data"]) == 2


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_share_msg_read(webserver_client: TestClient) -> None:
    status, body = await post_json(webserver_client, "/api/neng/v3/shareMsg/read", json={})
    assert status == 200
    assert body["code"] == 0
    assert body["message"] == "success"


@pytest.mark.usefixtures("clean_database")
async def test_neng_v3_share_msg_has_unread_msg(webserver_client: TestClient) -> None:
    status, body = await get_json(webserver_client, "/api/neng/v3/shareMsg/hasUnreadMsg")
    assert status == 200
    assert body["code"] == 0
    assert body["data"]["count"] == 0
    assert body["data"]["unRead"] is False
