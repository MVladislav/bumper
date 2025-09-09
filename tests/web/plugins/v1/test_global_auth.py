from aiohttp.test_utils import TestClient
import pytest

from bumper.web.response_utils import ERR_TOKEN_INVALID


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code(webserver_client: TestClient) -> None:
    # Test as global_e
    async with webserver_client.get(f"/v1/global/auth/getAuthCode?uid={None}&deviceId=dev_1234") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == ERR_TOKEN_INVALID
