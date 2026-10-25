import base64
import uuid

from aiohttp.test_utils import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import pytest

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils.account_key import account_public_key
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import _generate_uid
from bumper.web.envelope import ERR_TOKEN_INVALID, ERR_WRONG_EMAIL_ADDRESS, RETURN_API_SUCCESS

USER_ID = _generate_uid(bumper_isc.USER_USERNAME_DEFAULT)
_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


def _encrypt(value: str) -> str:
    """Encrypt a field the way the app does."""
    public_key = serialization.load_der_public_key(base64.b64decode(account_public_key()))
    if not isinstance(public_key, rsa.RSAPublicKey):
        msg = "the account key is not RSA"
        raise TypeError(msg)
    return base64.b64encode(public_key.encrypt(value.encode(), padding.PKCS1v15())).decode("ascii")


@pytest.mark.usefixtures("clean_database")
async def test_get_user_account_setting(webserver_client: TestClient) -> None:
    """The account setting response includes the device verification state."""
    async with webserver_client.get(f"{_PRIVATE}/userSetting/getUserAccountSetting") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] == {"deviceVerification": "DISABLED", "backUpEmail": None}


@pytest.mark.usefixtures("clean_database")
async def test_get_backup_email_for_an_account_without_one(webserver_client: TestClient) -> None:
    """An account without a backup email gets null email fields."""
    async with webserver_client.get(f"{_PRIVATE}/user/getBackupEmailByAccount?encryptAccount=opaque") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] == {"backUpEmail": None, "displayEmail": None}


@pytest.mark.usefixtures("clean_database")
async def test_bind_email_reports_the_new_address(webserver_client: TestClient) -> None:
    """The address bound to the account is the one the account shows."""
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    email = "new@example.com"
    async with webserver_client.get(
        f"{_PRIVATE}/user/bindEmail2",
        params={
            "uid": USER_ID,
            "bindType": "CHANGE",
            "encryptEmail": _encrypt(email),
            "verifyCode": bumper_isc.EMAIL_VERIFY_CODE,
            "verifyType": "EMAIL_CHANGE_BIND",
        },
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None
    async with webserver_client.get(f"{_PRIVATE}/user/getUserAccountInfo") as response:
        result = await response.json()
        assert result["data"]["email"] == email


@pytest.mark.usefixtures("clean_database")
async def test_bind_email_needs_the_verification_code(webserver_client: TestClient) -> None:
    """A wrong code leaves the account address as it was."""
    user_repo.add(USER_ID)
    async with webserver_client.get(
        f"{_PRIVATE}/user/bindEmail2",
        params={
            "uid": USER_ID,
            "encryptEmail": _encrypt("new@example.com"),
            "verifyCode": "000000",
        },
    ) as response:
        result = await response.json()
        assert result["code"] == "0001"
        assert result["success"] is False
    assert user_repo.get_by_id(USER_ID).email is None


@pytest.mark.usefixtures("clean_database")
async def test_add_backup_email_is_read_back(webserver_client: TestClient) -> None:
    """The backup email is stored and shown masked and in full."""
    user_repo.add(USER_ID)
    email = "backup@example.com"
    async with webserver_client.get(
        f"{_PRIVATE}/user/addBackupEmail",
        params={"uid": USER_ID, "encryptEmail": _encrypt(email), "serialNo": "undefined"},
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None
    async with webserver_client.get(
        f"{_PRIVATE}/user/getBackupEmailByAccount",
        params={"uid": USER_ID, "encryptAccount": "opaque"},
    ) as response:
        result = await response.json()
        assert result["data"] == {"backUpEmail": email, "displayEmail": "b***@example.com"}
    async with webserver_client.get(
        f"{_PRIVATE}/userSetting/getUserAccountSetting",
        params={"uid": USER_ID},
    ) as response:
        result = await response.json()
        assert result["data"]["backUpEmail"] == email


@pytest.mark.usefixtures("clean_database")
async def test_add_backup_email_rejects_a_value_it_cannot_read(webserver_client: TestClient) -> None:
    """A field that was not encrypted for this server is not stored."""
    user_repo.add(USER_ID)
    async with webserver_client.get(
        f"{_PRIVATE}/user/addBackupEmail",
        params={"uid": USER_ID, "encryptEmail": "opaque"},
    ) as response:
        result = await response.json()
        assert result["code"] == ERR_WRONG_EMAIL_ADDRESS
        assert result["success"] is False
    assert user_repo.get_by_id(USER_ID).backup_email is None


@pytest.mark.usefixtures("clean_database")
async def test_modify_password_is_accepted(webserver_client: TestClient) -> None:
    """A password change is answered without keeping the password."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/modifyPassword",
        params={"uid": USER_ID, "encryptNewPwd": "opaque"},
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] is None


@pytest.mark.usefixtures("clean_database")
async def test_get_login_history_returns_an_empty_page(webserver_client: TestClient) -> None:
    """There is no login history to report for the local test account."""
    async with webserver_client.get(f"{_PRIVATE}/user/loginHistory") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] == {"records": [], "hasNext": "N", "nextLastId": None}


@pytest.mark.usefixtures("clean_database")
async def test_check_user_device_serial_number(webserver_client: TestClient) -> None:
    """A serial is accepted only when it matches a registered bot name."""
    async with webserver_client.get(f"{_PRIVATE}/user/checkUserDeviceSN?sn=666") as response:
        result = await response.json()
        assert result["code"] == "0001"
        assert result["data"] is None
        assert result["success"] is False

    bot_repo.add("SN000000000000000001", "serial_check_bot", "p95mgv", "res", "eco-ng")
    async with webserver_client.get(f"{_PRIVATE}/user/checkUserDeviceSN?sn=SN000000000000000001") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"]["isCorrect"] == "Y"
        assert len(result["data"]["serialNo"]) == 32


@pytest.mark.usefixtures("clean_database")
async def test_user_data_apply_list_is_empty(webserver_client: TestClient) -> None:
    """The local service has no user data applications."""
    async with webserver_client.get(f"{_PRIVATE}/userData/applyList") as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["data"] == {"list": []}


@pytest.mark.usefixtures("clean_database")
async def test_check_login(webserver_client: TestClient) -> None:
    # An unknown device with no account is not a registration.
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == ERR_TOKEN_INVALID

    # Add a user to db and bind the device before checking again
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] != "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] != "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Remove dev from example user
    user_repo.remove_device(USER_ID, "dev_1234")

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    async with webserver_client.get(f"/v1/private/us/en/dev_1234/ios/1/0/0/user/checkLogin?accessToken={'token_1234'}") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] == "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]

    # Test again using global_e app
    user_repo.add(USER_ID)
    async with webserver_client.get(
        f"/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkLogin?accessToken={'token_1234'}",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "accessToken" in json_resp["data"]
        assert json_resp["data"]["accessToken"] == "token_1234"
        assert "uid" in json_resp["data"]
        assert "username" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_get_auth_code(webserver_client: TestClient) -> None:
    # Test without user or token
    async with webserver_client.get(
        f"/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid={None}&accessToken={None}",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == ERR_TOKEN_INVALID

    # Add a token to user and test
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "authCode" in json_resp["data"]
        assert "ecovacsUid" in json_resp["data"]

    # The above should have added an authcode to token, try again to test with existing authcode
    async with webserver_client.get(
        "/v1/private/us/en/dev_1234/ios/1/0/0/user/getAuthCode?uid=testuser&accessToken=token_1234",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert "authCode" in json_resp["data"]
        assert "ecovacsUid" in json_resp["data"]


@pytest.mark.usefixtures("clean_database")
async def test_check_agreement(webserver_client: TestClient) -> None:
    async with webserver_client.get("/v1/private/us/en/dev_1234/ios/1/0/0/user/checkAgreement") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS

    # Test as global_e
    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/checkAgreement") as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS


@pytest.mark.usefixtures("clean_database")
async def test_cancel_accept_agreement_batch(webserver_client: TestClient) -> None:
    """Withdrawing consent is accepted even though the agreements are fixed."""
    async with webserver_client.get(
        "/v1/private/de/en/dev_1234/global_e/3.16.0/google_play/1/user/cancelAcceptAgreementBatch",
        params={"agreementIds": "20230403095818_78798528690d2307bd692c0b624909f9"},
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert json_resp["data"] is None


@pytest.mark.usefixtures("clean_database")
async def test_change_lang(webserver_client: TestClient) -> None:
    """The app blocks the language switch on this response, so it must not 404."""
    async with webserver_client.get(
        "/v1/private/de/de/dev_1234/global_e/1/0/0/user/changeLang?fromLang=DE&toLang=EN",
    ) as resp:
        assert resp.status == 200
        json_resp = await resp.json()
        assert json_resp["code"] == RETURN_API_SUCCESS
        assert json_resp["success"] is True


@pytest.mark.usefixtures("clean_database")
async def test_logout_revokes_only_the_app_client(webserver_client: TestClient) -> None:
    """Logging out one app installation leaves the other client connected."""
    user = user_repo.create("private_logout_user")
    user_repo.bind_device(user.userid, "dev_1234")
    token_repo.add(user.userid, "token_one", client_id="client_one", resource="RES_ONE")
    token_repo.add(user.userid, "token_two", client_id="client_two", resource="RES_TWO")
    client_repo.add("client_one", user.userid, "ecouser.net", "RES_ONE", client_id="client_one")
    client_repo.add("client_two", user.userid, "ecouser.net", "RES_TWO", client_id="client_two")

    async with webserver_client.get(f"{_PRIVATE}/user/logout?accessToken=token_one") as resp:
        assert resp.status == 200
        result = await resp.json()

    assert result["code"] == RETURN_API_SUCCESS
    assert token_repo.get_by_token("token_one") is None
    assert token_repo.get_by_token("token_two") is not None
    assert client_repo.get(user.userid, client_id="client_one") is None
    assert client_repo.get(user.userid, client_id="client_two") is not None
    assert user_repo.get_by_id(user.userid) is not None


@pytest.mark.usefixtures("clean_database")
async def test_get_user_account_info(webserver_client: TestClient) -> None:
    user_repo.add(USER_ID)
    user_repo.add_device(USER_ID, "dev_1234")
    token_repo.add(USER_ID, "token_1234")
    token_repo.add_auth_code(USER_ID, "auth_1234")
    user_repo.add_bot(USER_ID, "did_1234")
    bot_repo.add("sn_1234", "did_1234", "class_1234", "res_1234", "com_1234")

    async with webserver_client.get("/v1/private/us/en/dev_1234/global_e/1/0/0/user/getUserAccountInfo") as resp:
        assert resp.status == 200
        json_resp = await resp.json()

    user = user_repo.get_by_id(USER_ID)
    assert user is not None
    assert json_resp["code"] == "0000"
    assert json_resp["msg"] == "Operation Successful"
    assert json_resp["data"]["uid"] == user.account_id
    assert json_resp["data"]["loginName"] == (user.login_name or user.username)


@pytest.mark.usefixtures("clean_database")
async def test_send_email_verify_code_returns_a_ticket(webserver_client: TestClient) -> None:
    """A request for an email code is answered with a ticket to check it."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/sendEmailVerifyCode?encryptEmail=opaque&verifyType=EMAIL_USER_DEVICE_SWITCH&supportChar=N",
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["success"] is True
        assert uuid.UUID(result["data"]["verifyId"])


@pytest.mark.usefixtures("clean_database")
async def test_check_email_verify_by_scene_accepts_the_code_of_the_page(webserver_client: TestClient) -> None:
    """The code the help page shows is always accepted."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/checkEmailVerifyByScene?verifyCode={bumper_isc.EMAIL_VERIFY_CODE}&scene=EMAIL_USER_DEVICE_SWITCH",
    ) as response:
        result = await response.json()
        assert result["code"] == RETURN_API_SUCCESS
        assert result["success"] is True


@pytest.mark.usefixtures("clean_database")
async def test_check_email_verify_by_scene_rejects_another_code(webserver_client: TestClient) -> None:
    """A code the page does not show is answered as a failure."""
    async with webserver_client.get(
        f"{_PRIVATE}/user/checkEmailVerifyByScene?verifyCode=000000&scene=EMAIL_USER_DEVICE_SWITCH",
    ) as response:
        result = await response.json()
        assert result["code"] == "0001"
        assert result["msg"] == "The verification code is not correct."
        assert result["success"] is False
