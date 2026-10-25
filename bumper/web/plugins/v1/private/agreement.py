"""Agreement plugin module."""

from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, bind
from bumper.web.payloads import agreement_entry

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}agreement/getUserAcceptInfo")
@bind(GL_V1)
async def _handle_get_user_accept_info(_: Request) -> Any:
    """Get user accept info."""
    now = int(utils.get_current_time_as_millis())
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    return {
        "acceptList": [
            agreement_entry(
                "20230403095818_78798528690d2307bd692c0b624909f9",
                "USER",
                "1.03",
                accept_time=now,
                domain=domain,
            ),
            agreement_entry(
                "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
                "PRIVACY",
                "1.07",
                accept_time=now,
                domain=domain,
            ),
        ],
        "newestList": [
            agreement_entry(
                "20230403095818_78798528690d2307bd692c0b624909f9",
                "USER",
                "1.03",
                force="N",
                domain=domain,
            ),
            agreement_entry(
                "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
                "PRIVACY",
                "1.07",
                force="N",
                domain=domain,
            ),
        ],
    }
