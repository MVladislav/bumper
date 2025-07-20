from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_get_product_iot_map(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/pim/product/getProductIotMap") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) > 0


@pytest.mark.usefixtures("clean_database")
async def test_get_confignet_all(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/pim/product/getConfignetAll") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_get_config_groups(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/pim/product/getConfigGroups") as resp:
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_software_config_batch(webserver_client: TestClient) -> None:
    # Test with known pid
    async with webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": ["5c19a8f3a1e6ee0001782247", "5e8e8d2a032edd3c03c66bf7"]},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2
        assert len(data["data"][0]["cfg"]) == 1

    # Test with unknown pid
    async with webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": ["test123", "test1234", "test12345"]},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 3
        assert len(data["data"][0]["cfg"]) == 0

    # Test with empty pids
    async with webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": []},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0


@pytest.mark.usefixtures("clean_database")
async def test_get_share_info(webserver_client: TestClient) -> None:
    async with webserver_client.post(
        "/api/pim/product/getShareInfo",
        json={"scene": "testscene"},
    ) as resp:
        assert resp.status == 200
        data = await resp.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
