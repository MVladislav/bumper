"""Tests for the account settings the app switches on and off."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import user_repo
from bumper.web.envelope import RETURN_API_SUCCESS

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_device_verification_switch_survives_a_reload(webserver_client: TestClient) -> None:
    """Enabling the passcode is what the account settings screen reads back."""
    user_repo.add("account_id")
    async with webserver_client.get(
        f"{_PRIVATE}/userSetting/modifyUserAccountSetting?settingKey=DEVICE_VERIFY&settingValue=ENABLED&uid=account_id",
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None
    async with webserver_client.get(f"{_PRIVATE}/userSetting/getUserAccountSetting?uid=account_id") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] == {"deviceVerification": "ENABLED", "backUpEmail": None}


@pytest.mark.usefixtures("clean_database")
async def test_device_verification_switch_can_be_turned_off(webserver_client: TestClient) -> None:
    """Disabling the passcode is reported the same way as enabling it."""
    user_repo.add("account_id")
    user_repo.set_device_verification("account_id", "ENABLED")
    async with webserver_client.get(
        f"{_PRIVATE}/userSetting/modifyUserAccountSetting?settingKey=DEVICE_VERIFY&settingValue=DISABLED&uid=account_id",
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
    async with webserver_client.get(f"{_PRIVATE}/userSetting/getUserAccountSetting?uid=account_id") as response:
        result = await response.json()
        assert result["data"]["deviceVerification"] == "DISABLED"


@pytest.mark.usefixtures("clean_database")
async def test_setting_of_an_unknown_account_is_ignored(webserver_client: TestClient) -> None:
    """A request for an account that does not exist writes no record."""
    async with webserver_client.get(
        f"{_PRIVATE}/userSetting/modifyUserAccountSetting?settingKey=DEVICE_VERIFY&settingValue=ENABLED&uid=missing",
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
    assert user_repo.list_all() == []
