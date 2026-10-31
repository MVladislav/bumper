"""Tests for message endpoints."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.envelope import RETURN_API_SUCCESS
from tests.web.helpers import get_json

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/1/0/0"


@pytest.mark.usefixtures("clean_database")
async def test_has_unread_msg(webserver_client: TestClient) -> None:
    status, json_resp = await get_json(webserver_client, f"{_PRIVATE}/message/hasUnreadMsg")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_msg_list(webserver_client: TestClient) -> None:
    status, json_resp = await get_json(webserver_client, f"{_PRIVATE}/message/getMsgList")
    assert status == 200
    assert json_resp["code"] == RETURN_API_SUCCESS
