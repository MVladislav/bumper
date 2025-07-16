import json

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.response_utils import ERR_TOKEN_INVALID


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code(webserver_client: TestClient) -> None:
    # Test as global_e
    resp = await webserver_client.get(f"/v1/global/auth/getAuthCode?uid={None}&deviceId=dev_1234")
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["code"] == ERR_TOKEN_INVALID
