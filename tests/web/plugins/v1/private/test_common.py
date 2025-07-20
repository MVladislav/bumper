from aiohttp.test_utils import TestClient
import pytest

from bumper.web.response_utils import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_check_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/checkVersion") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_check_app_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/common/checkAPPVersion") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_upload_device_info(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/common/uploadDeviceInfo") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_system_reminder(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/common/getSystemReminder") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


async def test_get_areas(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getAreas") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
