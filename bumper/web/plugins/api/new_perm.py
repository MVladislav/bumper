"""New-Perm plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.web.auth_util import generate_jwt_helper
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v3

_LOGGER = logging.getLogger(__name__)


class NewPermPlugin(WebserverPlugin):
    """New-Perm plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("POST", "/new-perm/token/sst/issue", _handle_sst_issue),
        ]


async def _handle_sst_issue(request: Request) -> Response:
    try:
        body = await request.json()
        acl = body.get("acl")
        exp_seconds = body.get("exp")
        sub = body.get("sub")

        if not acl or not exp_seconds or not sub:
            raise web.HTTPBadRequest(text="Missing required fields: acl, exp, sub")

        token, _ = await generate_jwt_helper(
            data={
                "acl": acl,
                "sub": sub,
                "grant": sub,
            },
            t="SST",
            exp_seconds=exp_seconds,
        )

        return response_success_v3(data={"data": {"token": f"SST.{token}"}}, msg="ok", msg_key="msg", result_key=None)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling SST token request"))
    raise HTTPInternalServerError
