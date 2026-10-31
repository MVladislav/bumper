"""Tests for the private device verification endpoints."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.db import user_repo
from tests.web.helpers import get_json

BASE = "/v1/private/DE/EN/device_id/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_get_current_device_returns_success(webserver_client: TestClient) -> None:
    """The app can open the device dynamic passcode flow."""
    device_id = "device_id"
    user_repo.add("user_id")
    user_repo.add_device("user_id", device_id)
    user_repo.set_device_name("user_id", device_id, "Test Phone")

    status, result = await get_json(webserver_client, f"{BASE}/device/getCurrent?uid=user_id")
    assert status == 200
    assert result["code"] == "0000"
    assert result["success"] is True
    assert result["data"] == {
        "exists": "Y",
        "verified": "Y",
        "deviceName": "Test Phone",
        "appDeviceId": "device_id",
        "browserCanvasHash": None,
        "deviceSource": "GAPP",
    }


@pytest.mark.usefixtures("clean_database")
async def test_generate_device_otp_returns_a_six_digit_code_and_ttl(webserver_client: TestClient) -> None:
    """Generate a short-lived local device dynamic passcode."""
    status, result = await get_json(webserver_client, f"{BASE}/device/otp/generate?uid=user_id")
    assert status == 200
    assert result["code"] == "0000"
    assert result["success"] is True
    data = result["data"]
    assert len(data["code"]) == 6
    assert data["ttlSeconds"] == 120
    assert data["expireAt"] - data["generatedAt"] == 120_000


@pytest.mark.usefixtures("clean_database")
async def test_device_otp_accepts_any_submitted_code(webserver_client: TestClient) -> None:
    """The device OTP verification succeeds without validating the code."""
    status, result = await get_json(
        webserver_client,
        f"{BASE}/verify/check?scene=MODIFY_PASSWORD&verifyMethod=DEVICE_OTP&deviceOtpCode=666666",
    )
    assert status == 200
    assert result["code"] == "0000"
    assert result["success"] is True
    assert result["data"] == {}


@pytest.mark.usefixtures("clean_database")
async def test_verify_check_does_not_accept_other_methods(webserver_client: TestClient) -> None:
    """Only the device OTP method is accepted by this endpoint implementation."""
    status, result = await get_json(webserver_client, f"{BASE}/verify/check?verifyMethod=EMAIL")
    assert status == 200
    assert result["code"] == 2004
    assert result["success"] is False


@pytest.mark.usefixtures("clean_database")
async def test_verify_check_requires_a_submitted_device_code(webserver_client: TestClient) -> None:
    """A device OTP request needs the passcode query parameter."""
    status, result = await get_json(webserver_client, f"{BASE}/verify/check?verifyMethod=DEVICE_OTP")
    assert status == 200
    assert result["code"] == 2004
    assert result["success"] is False
