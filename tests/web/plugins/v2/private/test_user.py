"""Tests for the account endpoints of the second API generation."""

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.envelope import RETURN_API_SUCCESS

_PRIVATE = "/v2/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_cancel_accept_agreement_batch_is_accepted(webserver_client: TestClient) -> None:
    """The withdrawal of consent is answered like the acceptance."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/cancelAcceptAgreementBatch",
        params={"uid": "account_id", "agreementIds": "20230403095818_78798528690d2307bd692c0b624909f9"},
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None


@pytest.mark.usefixtures("clean_database")
async def test_modify_password_is_accepted(webserver_client: TestClient) -> None:
    """The password change of the second generation is answered the same way."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/modifyPassword",
        params={"uid": "account_id", "encryptNewPwd": "opaque"},
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None
