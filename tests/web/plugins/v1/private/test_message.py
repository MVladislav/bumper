from aiohttp.test_utils import TestClient
import pytest

from bumper.web.utils.response_helper import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_has_unread_msg(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/message/hasUnreadMsg") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_msg_list(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/message/getMsgList") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
