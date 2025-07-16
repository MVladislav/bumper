import json

from aiohttp.test_utils import TestClient
import pytest


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
    resp = await webserver_client.post("/api/neng/message/hasUnreadMsg", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == 0
