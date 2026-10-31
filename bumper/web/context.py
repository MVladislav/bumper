"""The request context: what a handler needs to know about the request.

The body is parsed once and cached on the request, so the three spellings
that were spread over the handlers - `json.loads(await request.text())`,
`await request.json()` and `await request.post()` - become one call. The
identifiers stay apart on purpose: the user a caller names in the request is
kept apart from the user a token carries.
"""

from collections.abc import Mapping
import json
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.web.jwt import get_jwt_details, verify_jwt

BODY = web.RequestKey("body", Mapping[str, Any])
CLAIMS = web.RequestKey("claims", Mapping[str, Any])


async def read_body(request: Request) -> Mapping[str, Any]:
    """Return the body of the request as a mapping.

    A form encoded body and a JSON body are both read; anything else - a
    picture the robot uploads, for example - is left to the handler that
    knows what it is.
    """
    if (body := request.get(BODY)) is not None:
        cached: Mapping[str, Any] = body
        return cached

    parsed: Mapping[str, Any] = {}
    if request.content_type == "application/x-www-form-urlencoded":
        form = await request.post()
        parsed = {key: str(value) for key, value in form.items()}
    elif request.content_type == "application/json":
        text = await request.text()
        if text:
            decoded = json.loads(text)
            if isinstance(decoded, Mapping):
                parsed = dict(decoded)

    request[BODY] = parsed
    return parsed


def claims(request: Request) -> Mapping[str, Any] | None:
    """Return the claims of the bearer token, if the request carries one.

    The app sends the token on the `gl-*` API. The token is decoded, not
    verified against a signature, so a claim is still a name; it is kept
    apart from the name in the query so call sites do not mix the two.
    """
    if (cached := request.get(CLAIMS)) is not None:
        known: Mapping[str, Any] = cached
        return known

    details = get_jwt_details(request.headers.get("authorization"))
    if details is None:
        return None

    request[CLAIMS] = details
    return dict(details)


def verified_claims(request: Request) -> Mapping[str, Any] | None:
    """Return the claims of a token Bumper signed and that is still valid.

    Use this where the token decides what the caller may change, so a forged
    token cannot stand in for a name the request only carries.
    """
    scheme, _, token = (request.headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return verify_jwt(token.strip())


def device_id(request: Request) -> str | None:
    """Return the device id the path carries, if the path has one."""
    return request.match_info.get("devid")


def claimed_userid(request: Request) -> str | None:
    """Return the user the caller names, which nobody verified.

    The app names the user in the query string, in a header, or in an `auth`
    object in the body, depending on the endpoint. The name is used to look
    the user up, not to prove who they are.
    """
    if userid := request.query.get("userid"):
        return userid
    if userid := request.query.get("uid"):
        return userid
    if userid := request.headers.get("userid"):
        return userid
    if (auth := request.query.get("auth")) is not None:
        try:
            decoded = json.loads(auth) if isinstance(auth, str) else auth
        except ValueError:
            decoded = None
        if isinstance(decoded, Mapping) and (userid := decoded.get("userid")):
            return str(userid)
    return None
