from aiohttp.test_utils import TestClient
import pytest

from bumper.web.utils.response_helper import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_home_page_alert(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/campaign/homePageAlert") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
