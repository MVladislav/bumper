import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.response_utils import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_has_unread_msg(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/message/hasUnreadMsg")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_msg_list(webserver_client: TestClient) -> None:
    resp = await webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/message/getMsgList")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == RETURN_API_SUCCESS
