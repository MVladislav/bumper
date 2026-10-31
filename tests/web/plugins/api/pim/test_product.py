from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json, post_json


@pytest.mark.usefixtures("clean_database")
async def test_get_product_iot_map(webserver_client: TestClient) -> None:
    status, json_resp = await post_json(webserver_client, "/api/pim/product/getProductIotMap")
    assert status == 200
    assert json_resp["code"] == 0
    assert isinstance(json_resp["data"], list)
    assert len(json_resp["data"]) > 0


@pytest.mark.usefixtures("clean_database")
async def test_get_confignet_all(webserver_client: TestClient) -> None:
    status, data = await post_json(webserver_client, "/api/pim/product/getConfignetAll")
    assert status == 200
    assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_get_entry_group(webserver_client: TestClient) -> None:
    """productEntryGroup.json is a top-level array, not an object.

    Loading it as an object raised TypeError inside the handler and surfaced as
    a 500 to the app. Assert on the shape so a wrong loader is caught here.
    """
    status, json_resp = await get_json(webserver_client, "/api/pim/product/entry/group")
    assert status == 200
    assert json_resp["code"] == 0
    data = json_resp["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("name" in entry and "child" in entry for entry in data)


@pytest.mark.usefixtures("clean_database")
async def test_get_config_groups(webserver_client: TestClient) -> None:
    status, data = await post_json(webserver_client, "/api/pim/product/getConfigGroups")
    assert status == 200
    assert isinstance(data, dict)


@pytest.mark.usefixtures("clean_database")
async def test_software_config_batch(webserver_client: TestClient) -> None:
    status, data = await post_json(
        webserver_client,
        "/api/pim/product/software/config/batch",
        json={"pids": ["5c19a8f3a1e6ee0001782247", "5e8e8d2a032edd3c03c66bf7"]},
    )
    assert status == 200
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert len(data["data"][0]["cfg"]) == 1

    status, data = await post_json(
        webserver_client,
        "/api/pim/product/software/config/batch",
        json={"pids": ["test123", "test1234", "test12345"]},
    )
    assert status == 200
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 3
    assert len(data["data"][0]["cfg"]) == 0

    status, data = await post_json(
        webserver_client,
        "/api/pim/product/software/config/batch",
        json={"pids": []},
    )
    assert status == 200
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


@pytest.mark.usefixtures("clean_database")
async def test_get_share_info(webserver_client: TestClient) -> None:
    """The app reads `shareInfo` from the root of the document."""
    status, data = await post_json(
        webserver_client,
        "/api/pim/product/getShareInfo",
        json={"scene": "testscene"},
    )
    assert status == 200
    assert data["code"] == 0
    assert set(data["shareInfo"]) == {"keyword", "url", "shareText", "shareDesc", "shareUrl"}


@pytest.mark.usefixtures("clean_database")
async def test_product_setting_does_not_404(webserver_client: TestClient) -> None:
    """`GET /api/pim/product/setting?mids=…&modules=…` returned 404 twice a session."""
    status, body = await get_json(
        webserver_client,
        "/api/pim/product/setting?mids=300lc5,p95mgv&modules=fullStackYiko&lang=EN&a=undefined"
        "&p=android&c=undefined&country=DE&plat=android&userid=user_1234",
    )
    assert status == 200
    assert body["code"] == 0
    assert body["data"] == {}


@pytest.mark.usefixtures("clean_database")
async def test_product_setting_without_params(webserver_client: TestClient) -> None:
    status, _ = await get_json(webserver_client, "/api/pim/product/setting")
    assert status == 200
