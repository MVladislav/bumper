"""User plugin module."""

import logging
from typing import Any
import uuid

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request

from bumper.db import bot_repo, client_repo, identity, token_repo, user_repo
from bumper.utils.account_key import decrypt_account_field
from bumper.utils.settings import config as bumper_isc
from bumper.web import auth_service
from bumper.web.context import claimed_userid
from bumper.web.envelope import ERR_WRONG_EMAIL_ADDRESS, GL_V1, ApiError, bind
from bumper.web.hosts import adv_host
from bumper.web.jwt import verify_jwt
from bumper.web.payloads import AgreementEntry, agreement_entry, member_no, user_account_info

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()

routes.view(f"{BASE_URL}user/login")(bind(GL_V1)(auth_service.login))
routes.view(f"{BASE_URL}user/checkLogin")(bind(GL_V1)(auth_service.login))
routes.view(f"{BASE_URL}user/getAuthCode")(bind(GL_V1)(auth_service.get_auth_code))


@routes.view(f"{BASE_URL}user/addBackupEmail")
@bind(GL_V1)
async def _handle_add_backup_email(request: Request) -> None:
    """Store the address the account can be recovered with."""
    email = _encrypted_email(request)
    user_id = claimed_userid(request)
    if user_id is not None:
        user_repo.set_backup_email(user_id, email)


@routes.view(f"{BASE_URL}user/bindEmail2")
@bind(GL_V1)
async def _handle_bind_email(request: Request) -> None:
    """Bind the address the account is registered with."""
    _check_email_verify_code(request)
    email = _encrypted_email(request)
    user_id = claimed_userid(request)
    if user_id is not None:
        user_repo.set_email(user_id, email)


@routes.view(f"{BASE_URL}user/getBackupEmailByAccount")
@bind(GL_V1)
async def _handle_get_backup_email_by_account(request: Request) -> Any:
    """Get the backup email for the account."""
    user = user_repo.get_by_id(claimed_userid(request) or "")
    backup_email = user.backup_email if user is not None else None
    if backup_email is None:
        return {"backUpEmail": None, "displayEmail": None}
    return {"backUpEmail": backup_email, "displayEmail": _masked_email(backup_email)}


def _masked_email(email: str) -> str:
    """Hide all but the first character of the local part of an address."""
    local, _, domain = email.partition("@")
    if not local or not domain:
        return email
    return f"{local[0]}***@{domain}"


@routes.view(f"{BASE_URL}user/modifyPassword")
@bind(GL_V1)
async def handle_modify_password(_: Request) -> None:
    """Answer a password change."""


@routes.view(f"{BASE_URL}user/sendEmailVerifyCode")
@bind(GL_V1)
async def _handle_send_email_verify_code(_: Request) -> Any:
    """Answer a request for an email verification code with a ticket."""
    return {"verifyId": str(uuid.uuid4())}


@routes.view(f"{BASE_URL}user/checkEmailVerifyByScene")
@bind(GL_V1)
async def _handle_check_email_verify_by_scene(request: Request) -> None:
    """Check the code the account read from the mailbox."""
    if request.query.get("verifyCode", "") != bumper_isc.EMAIL_VERIFY_CODE:
        msg = "The verification code is not correct."
        raise ApiError(msg=msg, code="0001")


@routes.view(f"{BASE_URL}user/checkUserDeviceSN")
@bind(GL_V1)
async def _handle_check_user_device_sn(request: Request) -> Any:
    """Check the serial number of a device."""
    serial = request.query.get("sn", "").strip()
    bot = next((known_bot for known_bot in bot_repo.list_all() if known_bot.name.upper() == serial.upper()), None)
    if bot is None:
        msg = "SN Code does not exist"
        raise ApiError(msg=msg, code="0001")
    return {"isCorrect": "Y", "serialNo": uuid.uuid4().hex}


@routes.view(f"{BASE_URL}user/loginHistory")
@bind(GL_V1)
async def _handle_login_history(_: Request) -> Any:
    """Get the login history of the account."""
    return {"records": [], "hasNext": "N", "nextLastId": None}


@routes.view(f"{BASE_URL}userData/applyList")
@bind(GL_V1)
async def _handle_user_data_apply_list(_: Request) -> Any:
    """Get user data applications."""
    return {"list": []}


@routes.view(f"{BASE_URL}user/logout")
@bind(GL_V1)
async def _logout(request: Request) -> Any:
    """Revoke the token and client row of the app installation."""
    device_id = request.match_info.get("devid")
    access_token = request.query.get("accessToken")
    if device_id is not None and access_token is not None:
        user = user_repo.get_by_device_id(device_id)
        if user is None:
            _LOGGER.warning(f"No user found for {device_id} (logout)")
            return None

        token = token_repo.get_by_secret(access_token)
        if token is None and (details := verify_jwt(access_token)) is not None:
            auth_code = details.get("auth_code")
            if isinstance(auth_code, str):
                token = token_repo.get_by_auth_code(auth_code)

        owner = user_repo.get_by_id(token.userid) if token is not None else None
        if token is not None and owner is not None and owner.userid == user.userid:
            token_repo.revoke_token(owner.userid, token.token)
            if token.resource or token.client_id or token.device_id:
                client_repo.remove(
                    owner.userid,
                    resource=token.resource or None,
                    client_id=token.client_id or None,
                    device_id=token.device_id or None,
                )
    return None


@routes.view(f"{BASE_URL}user/getUserAccountInfo")
@bind(GL_V1)
async def _handle_get_user_account_info(request: Request) -> Any:
    """Get user account info."""
    user_device_id = request.match_info.get("devid", "")
    user = user_repo.get_by_device_id(user_device_id)
    if user is None:
        _LOGGER.warning(f"No user found for {user_device_id} (get_user_account_info)")
    else:
        return user_account_info(identity.ensure_public_ids(user))

    raise HTTPInternalServerError


@routes.view(f"{BASE_URL}user/checkAgreement")
@bind(GL_V1)
async def _handle_check_agreement(request: Request) -> Any:
    """Check agreement."""
    app_type = request.match_info.get("apptype", "")
    data: list[AgreementEntry] = []
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    if "global_" in app_type:
        data = [
            agreement_entry(
                "20180804040641_7d746faf18b8cb22a50d145598fe4c90",
                "USER",
                "1.01",
                accept_time=1681542128770,
                force="N",
                domain=domain,
            ),
            agreement_entry(
                "20180804040245_4e7c56dfb7ebd3b81b1f2747d0859fac",
                "PRIVACY",
                "1.01",
                accept_time=1681542128770,
                force="N",
                domain=domain,
            ),
        ]
    return data


@routes.view(f"{BASE_URL}user/checkAgreementBatch")
@bind(GL_V1)
async def handle_check_agreement_batch(_: Request) -> Any:
    """Check agreement batch."""
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    return [
        {
            "acceptTime": 1681542128770,
            "force": "N",
            "id": "20230403095818_78798528690d2307bd692c0b624909f9",
            "type": "USER",
            "url": None,
            "version": "1.03",
            "updateDesc": None,
        },
        {
            "acceptTime": 1681542128770,
            "force": "N",
            "id": "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
            "type": "PRIVACY",
            "url": None,
            "version": "1.07",
            "updateDesc": None,
        },
        {
            "acceptTime": 1681542128770,
            "force": "N",
            "id": "20251124143026_570d32ec1f78f36066b64193cd347e5b",
            "type": "PRIVACY",
            "url": f"{domain}?id=20251124143026_570d32ec1f78f36066b64193cd347e5b&language=EN",
            "version": "1.11",
            "updateDesc": None,
        },
    ]


@routes.view(f"{BASE_URL}user/getUserMenuInfo")
@bind(GL_V1)
async def _handle_get_user_menu_info(_: Request) -> Any:
    """Get user menu info."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return [
        {
            "menuItems": [
                {
                    "clickAction": 1,
                    "clickUri": "https://ecovacs.zendesk.com/hc/en-us",
                    "menuIconUrl": f"{domain}/2019/12/16/2019121603180741b73907046e742b80e8fe4a90fe2498.png",
                    "menuId": "20191216031849_4d744630f7ad2f5208a4b8051be61d10",
                    "menuName": "Help & Feedback",
                    "paramsJson": "",
                },
            ],
            "menuPositionKey": "A_FIRST",
        },
        {
            "menuItems": [
                {
                    "clickAction": 3,
                    "clickUri": "robotShare",
                    "menuIconUrl": f"{domain}/2019/12/16/2019121603284185e632ec6c5da10bd82119d7047a1f9e.png",
                    "menuId": "20191216032853_5fac4cc9cbd0e166dfa951485d1d8cc4",
                    "menuName": "Share Robot",
                    "paramsJson": "",
                },
            ],
            "menuPositionKey": "B_SECOND",
        },
        {
            "menuItems": [
                {
                    "clickAction": 3,
                    "clickUri": "config",
                    "menuIconUrl": f"{domain}/2019/12/16/201912160325324068da4e4a09b8c3973db162e84784d5.png",
                    "menuId": "20191216032545_ebea0fbb4cb02d9c2fec5bdf3371bc2d",
                    "menuName": "Settings",
                    "paramsJson": "",
                },
            ],
            "menuPositionKey": "C_THIRD",
        },
        {
            "menuItems": [
                {
                    "clickAction": 1,
                    "clickUri": f"https://{bumper_isc.DOMAIN_SEC6}/",
                    "menuIconUrl": f"{domain}/2019/12/16/201912160325324068da4e4a09b8c3973db162e84784d5.png",
                    "menuId": "20191216032545_ebea0fbb4cb02d9c2fec5bdf3371bc2c",
                    "menuName": "Bumper Status",
                    "paramsJson": "",
                },
            ],
            "menuPositionKey": "D_FOURTH",
        },
    ]


@routes.view(f"{BASE_URL}/user/getMyUserMenuInfo")
@routes.view(f"{BASE_URL}user/getMyUserMenuInfo")
@bind(GL_V1)
async def _handle_get_my_user_menu_info(_: Request) -> Any:
    """Get my user menu info."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return {
        "menuList": [
            {
                "menuItems": [
                    {
                        "clickAction": 3,
                        "clickUri": "glOrlderList",
                        "menuIconUrl": f"{domain}/2022/10/10/20221010104231_68dd6755a706e47113b110a6d5ec931a.png",
                        "menuId": "20221010104238_3f41cf9ecc1c44ebd39fc6e77a975067",
                        "menuName": "My Orders",
                        "menuSubName": "",
                        "paramsJson": "",
                        "redDotId": None,
                    },
                    {
                        "clickAction": 1,
                        "clickUri": f"https://{adv_host()}/pim/third_party_voice_control.html",
                        "menuIconUrl": f"{domain}/2022/12/14/20221214024053_10124672980fdcd4828fd5cbdf5c87ef.png",
                        "menuId": "20221214024100_207b336dcbcd6b96fb6b2c57fc14f095",
                        "menuName": "Third-party Voice Control",
                        "menuSubName": None,
                        "paramsJson": "",
                        "redDotId": None,
                    },
                    {
                        "clickAction": 3,
                        "clickUri": "helpfbView",
                        "menuIconUrl": f"{domain}/2022/05/10/20220510035541_93dd3bd6a9e4ee67eb4950d710f62ee1.png",
                        "menuId": "20220510035545_505adfaba38be91cd4426a5870173479",
                        "menuName": "Help & Feedback",
                        "menuSubName": None,
                        "paramsJson": "",
                        "redDotId": None,
                    },
                    {
                        "clickAction": 3,
                        "clickUri": "config",
                        "menuIconUrl": f"{domain}/2022/05/10/20220510035629_ac83db12a8ff972f1f611e8a549c18ab.png",
                        "menuId": "20220510035647_d2c7960a95f47b85158a0128ef562020",
                        "menuName": "Settings",
                        "menuSubName": None,
                        "paramsJson": "",
                        "redDotId": None,
                    },
                ],
                "menuPositionKey": "MY_A",
            },
        ],
    }


@routes.view(f"{BASE_URL}user/changeArea")
@routes.view(f"{BASE_URL}user/queryChangeArea")
@bind(GL_V1)
async def _handle_change_area(_: Request) -> Any:
    """Change area."""
    return {"isNeedReLogin": "N"}


@routes.view(f"{BASE_URL}user/changeLang")
@bind(GL_V1)
async def _handle_change_lang(_: Request) -> Any:
    """Change language."""
    return None


@routes.view(f"{BASE_URL}user/acceptAgreementBatch")
@bind(GL_V1)
async def _handle_accept_agreement_batch(_: Request) -> Any:
    """Accept agreement batch."""
    return None


@routes.view(f"{BASE_URL}user/cancelAcceptAgreementBatch")
@bind(GL_V1)
async def handle_cancel_accept_agreement_batch(_: Request) -> Any:
    """Cancel the acceptance of a batch of agreements."""
    return None


@routes.view(f"{BASE_URL}user/getMemberInfo")
@bind(GL_V1)
async def _handle_get_member_info(request: Request) -> Any:
    """Get Member Info."""
    user_id = request.query.get("uid")
    user_name = bumper_isc.USER_USERNAME_DEFAULT
    nickname = bumper_isc.USER_NICKNAME_DEFAULT
    email = bumper_isc.USER_MAIL_DEFAULT

    if user_id and (user := user_repo.get_by_id(user_id)):
        user_name = user.username
        nickname = user.nickname
        email = user.email or email
    return {
        "name": "smart eco",
        "memberNo": member_no(user_name),
        "userName": user_name,
        "integral": None,
        "exp": None,
        "headIco": None,
        "nickName": nickname,
        "mobile": None,
        "email": email,
        "isMember": None,
        "slogan": None,
        "sloganUrl": None,
        "expUpNeed": None,
        "userlevel": None,
        "userlevelName": "default",
        "levelList": None,
    }


@routes.view(f"{BASE_URL}user/center/modifyUserNickname")
@bind(GL_V1)
async def _handle_modify_user_nickname(request: Request) -> Any:
    """Change the display name of the user."""
    user_id = request.query.get("uid", "")
    nickname = request.query.get("nickname", "").strip()
    if not user_id or not nickname:
        _LOGGER.warning("No uid or nickname in the request")
        return None
    if user_repo.get_by_id(user_id) is None:
        _LOGGER.warning(f"No user found for {user_id} (modifyUserNickname)")
        return None
    user_repo.set_nickname(user_id, nickname)
    return None


def _encrypted_email(request: Request) -> str:
    """Read the address the app encrypted into the request."""
    email = decrypt_account_field(request.query.get("encryptEmail", ""))
    if email is None or "@" not in email:
        msg = "The email address is not valid."
        raise ApiError(msg=msg, code=ERR_WRONG_EMAIL_ADDRESS)
    return email


def _check_email_verify_code(request: Request) -> None:
    """Reject an email change without the code that was sent to the address."""
    if request.query.get("verifyCode", "") != bumper_isc.EMAIL_VERIFY_CODE:
        msg = "The verification code is not correct."
        raise ApiError(msg=msg, code="0001")
