"""User plugin module."""

from aiohttp import web

from bumper.web import auth_service
from bumper.web.envelope import GL_V1, bind
from bumper.web.plugins.v1.private.user import (
    handle_cancel_accept_agreement_batch,
    handle_check_agreement_batch,
    handle_modify_password,
)

from . import BASE_URL

routes = web.RouteTableDef()

routes.view(f"{BASE_URL}user/login")(bind(GL_V1)(auth_service.login))
routes.view(f"{BASE_URL}user/login2")(bind(GL_V1)(auth_service.login))
routes.view(f"{BASE_URL}user/checkLogin")(bind(GL_V1)(auth_service.login))
routes.view(f"{BASE_URL}user/checkAgreementBatch")(handle_check_agreement_batch)
routes.view(f"{BASE_URL}user/cancelAcceptAgreementBatch")(handle_cancel_accept_agreement_batch)
routes.view(f"{BASE_URL}user/modifyPassword")(handle_modify_password)
