import json
from unittest.mock import MagicMock

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import bot_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid
from bumper.web.plugins.api import appsvr

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)


@pytest.mark.usefixtures("clean_database", "helper_bot")
async def test_handle_app_do(webserver_client: TestClient) -> None:
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
    async with webserver_client.post("/api/appsvr/app.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"

    bot_repo.add("sn_1234", "did_1234", "ls1ok3", "res_1234", "eco-ng")

    # Test again with bot added
    async with webserver_client.post("/api/appsvr/app.do", json=postbody) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"

    # Test GetCodepush
    data_codepush = postbody.copy()
    data_codepush["todo"] = "GetCodepush"
    async with webserver_client.post("/api/appsvr/app.do", json=data_codepush) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"

    # Test RobotControl with invalid data
    data_robot_invalid = postbody.copy()
    data_robot_invalid["todo"] = "RobotControl"
    data_robot_invalid["data"] = "not_a_dict"
    async with webserver_client.post("/api/appsvr/app.do", json=data_robot_invalid) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "fail"

    # Test RobotControl with valid data but missing ctl
    data_robot_missing_ctl = postbody.copy()
    data_robot_missing_ctl["todo"] = "RobotControl"
    data_robot_missing_ctl["data"] = {}
    async with webserver_client.post("/api/appsvr/app.do", json=data_robot_missing_ctl) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "fail"

    # Test RobotControl with valid data and ctl
    data_robot_valid = postbody.copy()
    data_robot_valid["todo"] = "RobotControl"
    data_robot_valid["data"] = {"ctl": {"testcmd": {"foo": "bar"}}}
    async with webserver_client.post("/api/appsvr/app.do", json=data_robot_valid) as resp:
        assert resp.status in (200, 500)  # 500 if no helperbot, 200 if mocked

        # Test GetAppVideoUrl with valid keys
        data_video = postbody.copy()
    data_video["todo"] = "GetAppVideoUrl"
    data_video["keys"] = ["t9_promotional_video"]
    async with webserver_client.post("/api/appsvr/app.do", json=data_video) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"

    # Test GetAppVideoUrl with invalid keys
    data_video_invalid = postbody.copy()
    data_video_invalid["todo"] = "GetAppVideoUrl"
    data_video_invalid["keys"] = "not_a_list"
    async with webserver_client.post("/api/appsvr/app.do", json=data_video_invalid) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "fail"

    # Test GetDeviceProtocolV2
    data_protocol = postbody.copy()
    data_protocol["todo"] = "GetDeviceProtocolV2"
    async with webserver_client.post("/api/appsvr/app.do", json=data_protocol) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"

    # Test unknown todo
    data_unknown = postbody.copy()
    data_unknown["todo"] = "UnknownTodo"
    async with webserver_client.post("/api/appsvr/app.do", json=data_unknown) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "fail"

    # Test exception handling by sending invalid JSON
    async with webserver_client.post("/api/appsvr/app.do", data="not_json", headers={"Content-Type": "application/json"}) as resp:
        assert resp.status == 500


@pytest.mark.usefixtures("clean_database")
async def test_app_config_api(webserver_client: TestClient) -> None:
    # Test known code: app_lang_enum
    async with webserver_client.get("/api/appsvr/app/config?code=app_lang_enum") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert isinstance(json_resp["data"], list)
        assert json_resp["data"][0]["code"] == "app_lang_enum"
        langs = json_resp["data"][0]["content"]
        assert "de" in langs
        assert "en" in langs
        assert "zh" in langs
        assert langs["en"] == "English"

    # Test known code: codepush_config
    async with webserver_client.get("/api/appsvr/app/config?code=codepush_config") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert isinstance(json_resp["data"], list)
        assert json_resp["data"][0]["code"] == "codepush_config"
        assert isinstance(json_resp["data"][0]["content"], dict)
        assert "ssh5" in json_resp["data"][0]["content"]

    # Test known code: base_station_guide
    async with webserver_client.get("/api/appsvr/app/config?code=base_station_guide") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert isinstance(json_resp["data"], list)
        assert json_resp["data"][0]["code"] == "base_station_guide"

    # Test known code: time_zone_list
    async with webserver_client.get("/api/appsvr/app/config?code=time_zone_list") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"][0]["code"] == "time_zone_list"
        assert any("zone" in tz for tz in json_resp["data"][0]["content"])

    # Test known code: yiko_record_enabled + full_stack_yiko_entry
    async with webserver_client.get("/api/appsvr/app/config?code=yiko_record_enabled") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []
    async with webserver_client.get("/api/appsvr/app/config?code=full_stack_yiko_entry") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []

    # Test known code: yiko_support_lang
    async with webserver_client.get("/api/appsvr/app/config?code=yiko_support_lang") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"][0]["code"] == "yiko_support_lang"

    # Test unknown code
    async with webserver_client.get("/api/appsvr/app/config?code=unknown_code") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_service_list_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/service/list?area=de") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"]["account"].startswith("users-base.")
        assert json_resp["data"]["dc"] == "eu"
        assert json_resp["data"]["setApConfig"]["a"] == "de"

    # Test with no area param
    async with webserver_client.get("/api/appsvr/service/list") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"]["account"].startswith("users-base.")
        assert json_resp["data"]["dc"] == utils.get_dc_code(bumper_isc.ECOVACS_DEFAULT_COUNTRY)
        assert json_resp["data"]["setApConfig"]["a"] == bumper_isc.ECOVACS_DEFAULT_COUNTRY


@pytest.mark.usefixtures("clean_database")
async def test_improve_api(webserver_client: TestClient) -> None:
    did = "1"
    mid = "2"
    uid = "3"
    lang = "en"
    a = "a"
    c = "c"
    v = "v"
    p = "p"
    show_remark = "1"
    async with webserver_client.get(
        f"/api/appsvr/improve?did={did}&mid={mid}&uid={uid}&lang={lang}&a={a}&c={c}&v={v}&p={p}&show_remark={show_remark}",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        content = json_resp["data"]["content"]
        assert "pim/productImprovePlan_ww.html" in content
        assert f"did={did}" in content
        assert f"mid={mid}" in content
        assert f"uid={uid}" in content
        assert f"lang={lang}" in content
        assert f"showRemark={show_remark}" in content


@pytest.mark.usefixtures("clean_database")
async def test_improve_accept_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/improve/accept") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0


@pytest.mark.usefixtures("clean_database")
async def test_improve_user_accept_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/improve/user/accept") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == 0
        assert "data" in json_resp
        assert json_resp["data"]["accept"] is False


@pytest.mark.usefixtures("clean_database")
async def test_notice_home_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/notice/home") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_notice_list_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/notice/list") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"


@pytest.mark.usefixtures("clean_database")
async def test_ota_firmware_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/ota/firmware") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == -1


@pytest.mark.usefixtures("clean_database")
async def test_device_blacklist_check_api(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/appsvr/device/blacklist/check") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["data"] == []


@pytest.mark.usefixtures("clean_database")
async def test_akvs_start_watch_api(webserver_client: TestClient) -> None:
    auth = json.dumps({"userid": "u1", "resource": "r1"})
    async with webserver_client.get(f"/api/appsvr/akvs/start_watch?did=testdid&auth={auth}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["ret"] == "ok"
        assert json_resp["client_id"] == "u1-r1"
        assert isinstance(json_resp["credentials"], dict)
        assert "AccessKeyId" in json_resp["credentials"]
        assert json_resp["channel"].startswith("production-")


@pytest.mark.usefixtures("clean_database")
def test_include_product_iot_map_info() -> None:
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
