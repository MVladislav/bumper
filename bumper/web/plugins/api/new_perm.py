"""New-Perm plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.auth_service import generate_jwt_helper
from bumper.web.context import read_body
from bumper.web.envelope import LEGACY, bind

from . import PREFIX

routes = web.RouteTableDef()


@routes.post(f"{PREFIX}/new-perm/token/sst/issue")
@bind(LEGACY.with_result(None).with_msg(("msg", "success")))
async def _handle_sst_issue(request: Request) -> Any:
    body = await read_body(request)
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

    return {"data": {"token": f"SST.{token}"}}
