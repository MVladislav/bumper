from aiohttp.test_utils import TestClient
import pytest

from bumper.web.response_utils import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_ad_by_position_type(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/ad/getAdByPositionType") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_boot_screen(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/ad/getBootScreen") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
