"""Tests for bumper/web/plugins/v1/private/intl.py."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import user_repo
from bumper.web.envelope import RETURN_API_SUCCESS
from bumper.web.payloads import member_integral
from tests.web.helpers import get_json

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_basic_info_returns_member_integral_for_known_device(
    webserver_client: TestClient,
) -> None:
    user_repo.add("user_id")
    user_repo.add_device("user_id", "dev_1234")

    status, result = await get_json(webserver_client, f"{_PRIVATE}/intl/member/basicInfo")
    assert status == 200
    assert result["code"] == RETURN_API_SUCCESS
    assert result["data"] == member_integral()


@pytest.mark.usefixtures("clean_database")
async def test_basic_info_fails_without_a_known_device(
    webserver_client: TestClient,
) -> None:
    async with webserver_client.get(f"{_PRIVATE}/intl/member/basicInfo") as response:
        assert response.status == 500


@pytest.mark.usefixtures("clean_database")
async def test_sign_status_returns_sign(webserver_client: TestClient) -> None:
    status, result = await get_json(webserver_client, f"{_PRIVATE}/intl/member/signStatus")
    assert status == 200
    assert result["code"] == RETURN_API_SUCCESS
    assert result["data"] == {"signStatus": "SIGN"}
