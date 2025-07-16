import json

from aiohttp.test_utils import TestClient
import pytest


@pytest.mark.usefixtures("clean_database")
async def test_get_product_iot_map(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/api/pim/product/getProductIotMap")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == 0
    assert isinstance(jsonresp["data"], list)
    assert len(jsonresp["data"]) > 0


@pytest.mark.usefixtures("clean_database")
async def test_get_confignet_all(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/api/pim/product/getConfignetAll")
    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_get_config_groups(webserver_client: TestClient) -> None:
    resp = await webserver_client.post("/api/pim/product/getConfigGroups")
    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_software_config_batch(webserver_client: TestClient) -> None:
    # Test with known pid
    resp = await webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": ["5c19a8f3a1e6ee0001782247", "5e8e8d2a032edd3c03c66bf7"]},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert len(data["data"][0]["cfg"]) == 1

    # Test with unknown pid
    resp = await webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": ["test123", "test1234", "test12345"]},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 3
    assert len(data["data"][0]["cfg"]) == 0

    # Test with empty pids
    resp = await webserver_client.post(
        "/api/pim/product/software/config/batch",
        json={"pids": []},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


@pytest.mark.usefixtures("clean_database")
async def test_get_share_info(webserver_client: TestClient) -> None:
    resp = await webserver_client.post(
        "/api/pim/product/getShareInfo",
        json={"scene": "testscene"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
