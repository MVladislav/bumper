import asyncio
import json

import pytest

from bumper.db import bot_repo
from bumper.mqtt.helper_bot import MQTTHelperBot
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


@pytest.mark.usefixtures("clean_database")
async def test_lg_logs(webserver_client, helper_bot: MQTTHelperBot) -> None:
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
    resp = await webserver_client.post("/api/lg/log.do", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["ret"] == "ok"
    assert len(jsonresp["logs"]) == 0
