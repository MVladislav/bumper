"""Device plugin module."""

import secrets
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.db import user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, ApiError, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}device/getCurrent")
@bind(GL_V1)
async def _handle_get_current_device(request: Request) -> dict[str, Any]:
    """Get current device."""
    device_id = request.match_info.get("devid", "")
    user = user_repo.get_by_device_id(device_id)
    registered = user is not None and device_id in user.devices
    device_name = user.device_names.get(device_id, "Bumper") if user is not None else "Bumper"
    return {
        "exists": "Y" if registered else "N",
        "verified": "Y" if registered else "N",
        "deviceName": device_name,
        "appDeviceId": device_id,
        "browserCanvasHash": None,
        "deviceSource": "GAPP",
    }


@routes.view(f"{BASE_URL}device/otp/generate")
@bind(GL_V1)
async def _handle_generate_device_otp(_: Request) -> dict[str, Any]:
    """Generate a device dynamic passcode."""
    generated_at = utils.get_current_time_as_millis()
    return {
        "code": f"{secrets.randbelow(1_000_000):06d}",
        "generatedAt": generated_at,
        "expireAt": generated_at + bumper_isc.DEVICE_OTP_TTL_SECONDS * 1000,
        "ttlSeconds": bumper_isc.DEVICE_OTP_TTL_SECONDS,
    }


@routes.view(f"{BASE_URL}verify/check")
@bind(GL_V1)
async def _handle_verify_check(request: Request) -> dict[str, Any]:
    """Check a verification code."""
    if request.query.get("verifyMethod") == "DEVICE_OTP":
        if "deviceOtpCode" in request.query:
            # Device dynamic passcodes are not provisioned by the local server.
            # Treat a submitted code as accepted so the app can continue its flow.
            return {}
        msg = "Device dynamic passcode is missing"
        raise ApiError(msg=msg, code=2004)

    msg = "Unsupported verification method"
    raise ApiError(msg=msg, code=2004)
