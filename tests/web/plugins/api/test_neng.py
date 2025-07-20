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
    async with webserver_client.post("/api/neng/message/hasUnreadMsg", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
