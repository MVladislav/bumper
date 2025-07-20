from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_lg_logs(webserver_client: TestClient) -> None:
    test_did = "did_1234"
    bot_repo.add("sn_1234", test_did, "ls1ok3", "res_1234", "eco-ng")
    bot_repo.set_mqtt(test_did, True)

    # Test GetGlobalDeviceList
    postbody = {
        "auth": {
            "realm": "ecouser.net",
            "resource": "ECOGLOBLEac5ae987",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "did": test_did,
        "resource": "res_1234",
        "td": "GetCleanLogs",
    }
    async with webserver_client.post("/api/lg/log.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert len(json_resp["logs"]) == 0
