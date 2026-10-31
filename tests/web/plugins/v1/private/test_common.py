import base64
import json

from aiohttp.test_utils import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
import pytest

from bumper.db import user_repo
from bumper.web.envelope import RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_check_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/checkVersion") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_check_app_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/common/checkAPPVersion") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_upload_device_info(webserver_client: TestClient) -> None:
    device_id = "reported_device_id"
    user_repo.add("account_id")
    user_repo.add_device("account_id", device_id)
    async with webserver_client.get(
        f"/v1/private/us/en/{device_id}/global_e/1/0/0/common/uploadDeviceInfo?deviceNum={device_id}&model=Test Phone",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
    assert user_repo.get_by_id("account_id").device_names == {device_id: "Test Phone"}


@pytest.mark.usefixtures("clean_database")
async def test_get_user_device_returns_the_current_app_device(webserver_client: TestClient) -> None:
    """The account device screen lists the local app device."""
    device_id = "test_device_id"
    user_repo.add("account_id")
    user_repo.add_device("account_id", device_id)
    user_repo.set_device_name("account_id", device_id, "Test Phone")

    async with webserver_client.get(
        f"/v1/private/us/en/{device_id}/global_e/3.16.0/google_play/1/common/getUserDevice?uid=account_id",
    ) as response:
        assert response.status == 200
        data = (await response.json())["data"]
        device = data["userDeviceList"][0]
        assert data["helpModule"] is None
        assert device["id"] == device_id
        assert device["deviceName"] == "Test Phone"
        assert device["isCurrentDevice"] == "Y"
        assert isinstance(device["lastLoginTime"], str)
        assert device["isTrust"] == "N"


@pytest.mark.usefixtures("clean_database")
async def test_delete_user_device_answers_successfully(webserver_client: TestClient) -> None:
    """Removing a saved app device is acknowledged."""
    user_repo.add("account_to_delete")
    user_repo.add_device("account_to_delete", "old-device")
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1/common/deleteUserDevice?uid=account_to_delete&userDeviceId=old-device",
    ) as response:
        assert response.status == 200
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None
    assert "old-device" not in user_repo.get_by_id("account_to_delete").devices


@pytest.mark.usefixtures("clean_database")
async def test_get_all_service_info_reports_local_support_options(webserver_client: TestClient) -> None:
    """The service directory does not advertise unavailable cloud support."""
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1/common/getAllServiceInfo",
    ) as response:
        assert response.status == 200
        data = (await response.json())["data"]
        assert data["phoneServiceInfo"]["isSupport"] == "N"
        assert data["emailInfo"]["isSupport"] == "N"


@pytest.mark.usefixtures("clean_database")
async def test_get_system_reminder(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/common/getSystemReminder") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_areas(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getAreas") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_get_config(webserver_client: TestClient) -> None:
    """Test /common/getConfig endpoint with various keys."""
    # Test with a single key (PUBLIC.KEY.CONFIG)
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getConfig?keys=PUBLIC.KEY.CONFIG") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) == 1
        assert json_resp["data"][0]["key"] == "PUBLIC.KEY.CONFIG"
        # Verify the public key is present and properly formatted
        config_value = json.loads(json_resp["data"][0]["value"])
        assert "publicKey" in config_value
        assert isinstance(config_value["publicKey"], str)
        public_key = serialization.load_der_public_key(base64.b64decode(config_value["publicKey"]))
        assert isinstance(public_key, RSAPublicKey)

    # Test with multiple keys
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/ios/1/0/0/common/getConfig?keys=EMAIL.REGISTER.CONFIG,USER.DATA.COLLECTION,PRIVACY.CONFIG",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) == 3

        # Process each config item individually
        config_dict = {}
        for item in json_resp["data"]:
            key = item["key"]
            value = item["value"]
            try:
                # Try to parse as JSON if it's a string
                if isinstance(value, str):
                    config_dict[key] = json.loads(value)
                else:
                    config_dict[key] = value
            except json.JSONDecodeError:
                # If not valid JSON, store as-is
                config_dict[key] = value

        # Verify EMAIL.REGISTER.CONFIG
        assert "EMAIL.REGISTER.CONFIG" in config_dict
        assert config_dict["EMAIL.REGISTER.CONFIG"]["needVerify"] == "N"

        # Verify USER.DATA.COLLECTION (this is a plain string "N")
        assert "USER.DATA.COLLECTION" in config_dict
        assert config_dict["USER.DATA.COLLECTION"] == "N"

        # Verify PRIVACY.CONFIG
        assert "PRIVACY.CONFIG" in config_dict
        assert isinstance(config_dict["PRIVACY.CONFIG"], list)
        assert len(config_dict["PRIVACY.CONFIG"]) == 2
        assert config_dict["PRIVACY.CONFIG"][0]["key"] == "PERSONAL_INFO_SHARING"
        assert config_dict["PRIVACY.CONFIG"][0]["status"] == "DISABLED"

    # Test with all possible keys
    all_keys = [
        "PUBLIC.KEY.CONFIG",
        "EMAIL.REGISTER.CONFIG",
        "OPEN.APP.CERTIFICATE.CONFIG",
        "USER.DATA.COLLECTION",
        "USER.DEVICE.LIST.CONFIG",
        "PRIVACY.CONFIG",
        "FIND.PASSWORD.FAQ.CONF",
        "PASSWORD.STRENGTH.URL",
        "SUGGESTION.DEFAULT.FLAG",
        "DEVICE.OTP.CONFIG",
        "AREA.CONFIG",
    ]
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/common/getConfig?keys={','.join(all_keys)}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) == len(all_keys)

        # Verify all keys are present
        returned_keys = [item["key"] for item in json_resp["data"]]
        for key in all_keys:
            assert key in returned_keys

        # The app shows the option to export the data of the account when
        # the flag of the area config is on.
        area = next(item for item in json_resp["data"] if item["key"] == "AREA.CONFIG")
        assert json.loads(area["value"])["sensitiveDataExportFlag"] == "N"

        device_otp = next(item for item in json_resp["data"] if item["key"] == "DEVICE.OTP.CONFIG")
        assert json.loads(device_otp["value"]) == {"ttlSeconds": 120}


@pytest.mark.usefixtures("clean_database")
async def test_get_user_config_no_user(webserver_client: TestClient) -> None:
    """Test /common/getUserConfig endpoint with non-existent device ID."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getUserConfig") as resp:
        assert resp.status == 500  # Expect 500 when no user is found


@pytest.mark.usefixtures("clean_database")
async def test_get_user_config_with_user(webserver_client: TestClient) -> None:
    """Test /common/getUserConfig endpoint with an existing user."""
    user_repo.add(user_id="test_user")
    user_repo.add_device(user_id="test_user", did="dev_1234")

    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getUserConfig") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "saTraceConfig" in json_resp["data"]
        assert json_resp["data"]["saTraceConfig"]["collectionStatus"] == "DISABLED"


@pytest.mark.usefixtures("clean_database")
async def test_get_area_support_service(webserver_client: TestClient) -> None:
    """Test /common/getAreaSupportService endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getAreaSupportService") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert json_resp["data"]["isSelfHelpRepair"] == "N"


@pytest.mark.usefixtures("clean_database")
async def test_get_agreement_url_batch(webserver_client: TestClient) -> None:
    """Test /common/getAgreementURLBatch endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getAgreementURLBatch") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) == 2
        assert json_resp["data"][0]["type"] == "USER"
        assert json_resp["data"][1]["type"] == "PRIVACY"


@pytest.mark.usefixtures("clean_database")
async def test_get_timestamp(webserver_client: TestClient) -> None:
    """Test /common/getTimestamp endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getTimestamp") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "timestamp" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_get_about_brief_item(webserver_client: TestClient) -> None:
    """Test /common/getAboutBriefItem endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getAboutBriefItem") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)


@pytest.mark.usefixtures("clean_database")
async def test_get_bottom_navigate_info_list(webserver_client: TestClient) -> None:
    """Test /common/getBottomNavigateInfoList endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getBottomNavigateInfoList") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert isinstance(json_resp["data"], list)
        assert len(json_resp["data"]) == 3
        assert json_resp["data"][0]["iconType"] == "ROBOT"
        assert json_resp["data"][1]["iconType"] == "MALL"
        assert json_resp["data"][2]["iconType"] == "MINE"


@pytest.mark.usefixtures("clean_database")
async def test_get_current_area_support_service_info(webserver_client: TestClient) -> None:
    """Test /common/getCurrentAreaSupportServiceInfo endpoint."""
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/common/getCurrentAreaSupportServiceInfo") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "intlFeedbackStartInfo" in json_resp["data"]
        assert "liveChatInfo" in json_resp["data"]
        assert "phoneServiceInfo" in json_resp["data"]
        assert json_resp["data"]["phoneServiceInfo"]["email"] == "bumper@home.local"
