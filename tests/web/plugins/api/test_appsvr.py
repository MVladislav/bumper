import json
from unittest.mock import MagicMock

import pytest

from bumper.db import bot_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_util import _generate_uid
from bumper.web.plugins.api import appsvr

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database")
async def test_handle_app_do(webserver_client) -> None:
    # Test GetGlobalDeviceList
    postbody = {
        "aliliving": False,
        "appVer": "1.1.6",
        "auth": {
            "realm": "ecouser.net",
            "resource": "ECOGLOBLEac5ae987",
            "token": "token_1234",
            "userid": USER_ID,
            "with": "users",
        },
        "channel": "google_play",
        "defaultLang": "en",
        "lang": "en",
        "platform": "Android",
        "todo": "GetGlobalDeviceList",
        "userid": USER_ID,
    }
    resp = await webserver_client.post("/api/appsvr/app.do", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["ret"] == "ok"

    bot_repo.add("sn_1234", "did_1234", "ls1ok3", "res_1234", "eco-ng")

    # Test again with bot added
    resp = await webserver_client.post("/api/appsvr/app.do", json=postbody)
    assert resp.status == 200
    text = await resp.text()
    jsonresp = json.loads(text)
    assert jsonresp["ret"] == "ok"

    # Test GetCodepush
    data_codepush = postbody.copy()
    data_codepush["todo"] = "GetCodepush"
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_codepush)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"

    # Test RobotControl with invalid data
    data_robot_invalid = postbody.copy()
    data_robot_invalid["todo"] = "RobotControl"
    data_robot_invalid["data"] = "not_a_dict"
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_robot_invalid)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "fail"

    # Test RobotControl with valid data but missing ctl
    data_robot_missing_ctl = postbody.copy()
    data_robot_missing_ctl["todo"] = "RobotControl"
    data_robot_missing_ctl["data"] = {}
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_robot_missing_ctl)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "fail"

    # Test RobotControl with valid data and ctl
    data_robot_valid = postbody.copy()
    data_robot_valid["todo"] = "RobotControl"
    data_robot_valid["data"] = {"ctl": {"testcmd": {"foo": "bar"}}}
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_robot_valid)
    assert resp.status in (200, 500)  # 500 if no helperbot, 200 if mocked

    # Test GetAppVideoUrl with valid keys
    data_video = postbody.copy()
    data_video["todo"] = "GetAppVideoUrl"
    data_video["keys"] = ["t9_promotional_video"]
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_video)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"

    # Test GetAppVideoUrl with invalid keys
    data_video_invalid = postbody.copy()
    data_video_invalid["todo"] = "GetAppVideoUrl"
    data_video_invalid["keys"] = "not_a_list"
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_video_invalid)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "fail"

    # Test GetDeviceProtocolV2
    data_protocol = postbody.copy()
    data_protocol["todo"] = "GetDeviceProtocolV2"
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_protocol)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"

    # Test unknown todo
    data_unknown = postbody.copy()
    data_unknown["todo"] = "UnknownTodo"
    resp = await webserver_client.post("/api/appsvr/app.do", json=data_unknown)
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "fail"

    # Test exception handling by sending invalid JSON
    resp = await webserver_client.post("/api/appsvr/app.do", data="not_json", headers={"Content-Type": "application/json"})
    assert resp.status == 500


@pytest.mark.usefixtures("clean_database")
async def test_app_config_api(webserver_client):
    # Test known code: app_lang_enum
    resp = await webserver_client.get("/api/appsvr/app/config?code=app_lang_enum")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert isinstance(jsonresp["data"], list)
    assert jsonresp["data"][0]["code"] == "app_lang_enum"
    langs = jsonresp["data"][0]["content"]
    assert "de" in langs
    assert "en" in langs
    assert "zh" in langs
    assert langs["en"] == "English"

    # Test known code: codepush_config
    resp = await webserver_client.get("/api/appsvr/app/config?code=codepush_config")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert isinstance(jsonresp["data"], list)
    assert jsonresp["data"][0]["code"] == "codepush_config"
    assert isinstance(jsonresp["data"][0]["content"], dict)
    assert "ssh5" in jsonresp["data"][0]["content"]

    # Test known code: base_station_guide
    resp = await webserver_client.get("/api/appsvr/app/config?code=base_station_guide")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert isinstance(jsonresp["data"], list)
    assert jsonresp["data"][0]["code"] == "base_station_guide"

    # Test known code: time_zone_list
    resp = await webserver_client.get("/api/appsvr/app/config?code=time_zone_list")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"][0]["code"] == "time_zone_list"
    assert any("zone" in tz for tz in jsonresp["data"][0]["content"])

    # Test known code: yiko_record_enabled + full_stack_yiko_entry
    resp = await webserver_client.get("/api/appsvr/app/config?code=yiko_record_enabled")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"] == []
    resp = await webserver_client.get("/api/appsvr/app/config?code=full_stack_yiko_entry")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"] == []

    # Test known code: yiko_support_lang
    resp = await webserver_client.get("/api/appsvr/app/config?code=yiko_support_lang")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"][0]["code"] == "yiko_support_lang"

    # Test unknown code
    resp = await webserver_client.get("/api/appsvr/app/config?code=unknown_code")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_service_list_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/service/list?area=de")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"]["account"].startswith("users-base.")
    assert jsonresp["data"]["dc"] == "eu"
    assert jsonresp["data"]["setApConfig"]["a"] == "de"

    # Test with no area param
    resp = await webserver_client.get("/api/appsvr/service/list")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"]["account"].startswith("users-base.")
    assert jsonresp["data"]["dc"] == utils.get_dc_code(bumper_isc.ECOVACS_DEFAULT_COUNTRY)
    assert jsonresp["data"]["setApConfig"]["a"] == bumper_isc.ECOVACS_DEFAULT_COUNTRY


@pytest.mark.usefixtures("clean_database")
async def test_improve_api(webserver_client):
    did = "1"
    mid = "2"
    uid = "3"
    lang = "en"
    a = "a"
    c = "c"
    v = "v"
    p = "p"
    show_remark = "1"
    resp = await webserver_client.get(
        f"/api/appsvr/improve?did={did}&mid={mid}&uid={uid}&lang={lang}&a={a}&c={c}&v={v}&p={p}&show_remark={show_remark}",
    )
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["code"] == 0
    content = jsonresp["data"]["content"]
    assert "pim/productImprovePlan_ww.html" in content
    assert f"did={did}" in content
    assert f"mid={mid}" in content
    assert f"uid={uid}" in content
    assert f"lang={lang}" in content
    assert f"showRemark={show_remark}" in content


@pytest.mark.usefixtures("clean_database")
async def test_improve_accept_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/improve/accept")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["code"] == 0


@pytest.mark.usefixtures("clean_database")
async def test_improve_user_accept_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/improve/user/accept")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["code"] == 0
    assert "data" in jsonresp
    assert jsonresp["data"]["accept"] is False


@pytest.mark.usefixtures("clean_database")
async def test_notice_home_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/notice/home")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_notice_list_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/notice/list")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_ota_firmware_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/ota/firmware")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["code"] == -1


@pytest.mark.usefixtures("clean_database")
async def test_device_blacklist_check_api(webserver_client):
    resp = await webserver_client.get("/api/appsvr/device/blacklist/check")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_akvs_start_watch_api(webserver_client):
    auth = json.dumps({"userid": "u1", "resource": "r1"})
    resp = await webserver_client.get(f"/api/appsvr/akvs/start_watch?did=testdid&auth={auth}")
    assert resp.status == 200
    jsonresp = json.loads(await resp.text())
    assert jsonresp["ret"] == "ok"
    assert jsonresp["client_id"] == "u1-r1"
    assert isinstance(jsonresp["credentials"], dict)
    assert "AccessKeyId" in jsonresp["credentials"]
    assert jsonresp["channel"].startswith("production-")


def test_include_product_iot_map_info():
    bot = MagicMock()
    bot.class_id = "ls1ok3"
    bot.mqtt_connection = True
    bot.xmpp_connection = False
    bot.as_dict.return_value = {"class_id": "ls1ok3", "mqtt_connection": True, "xmpp_connection": False}
    # Patch get_product_iot_map to return a matching classid
    appsvr.get_product_iot_map = lambda: [
        {
            "classid": "ls1ok3",
            "product": {
                "_id": "pid1",
                "materialNo": "mat1",
                "name": "DEEBOT X",
                "model": "m1",
                "UILogicId": "ui1",
                "ota": {},
                "iconUrl": "icon1",
            },
        },
    ]
    result = appsvr._include_product_iot_map_info(bot)
    assert result is not None
    assert result["pid"] == "pid1"
    assert result["product_category"] == "DEEBOT"
    assert result["deviceName"] == "DEEBOT X"
    assert result["model"] == "m1"
    assert result["icon"] == "icon1"
    assert result["status"] == 1
    assert result["shareable"] is True
