"""Agreement plugin module."""

from collections.abc import Iterable

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.utils.response_helper import response_success_v1

from . import BASE_URL


class AgreementPlugin(WebserverPlugin):
    """Agreement plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}agreement/getUserAcceptInfo", _handle_get_user_accept_info),
        ]


async def _handle_get_user_accept_info(_: Request) -> Response:
    """Get user accept info."""
    domain = f"https://{bumper_isc.DOMAIN_SEC3}/content/agreement"
    return response_success_v1(
        {
            "acceptList": [
                {
                    "acceptTime": 1681542125538,
                    "force": None,
                    "id": "20230403095818_78798528690d2307bd692c0b624909f9",
                    "type": "USER",
                    "updateDesc": None,
                    "url": f"{domain}?id=20230403095818_78798528690d2307bd692c0b624909f9&language=EN",
                    "version": "1.03",
                },
                {
                    "acceptTime": 1681542128770,
                    "force": None,
                    "id": "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
                    "type": "PRIVACY",
                    "updateDesc": None,
                    "url": f"{domain}?id=20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733&language=EN",
                    "version": "1.07",
                },
            ],
            "newestList": [
                {
                    "acceptTime": None,
                    "force": "N",
                    "id": "20230403095818_78798528690d2307bd692c0b624909f9",
                    "type": "USER",
                    "updateDesc": None,
                    "url": f"{domain}?id=20230403095818_78798528690d2307bd692c0b624909f9&language=EN",
                    "version": "1.03",
                },
                {
                    "acceptTime": None,
                    "force": "N",
                    "id": "20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733",
                    "type": "PRIVACY",
                    "updateDesc": None,
                    "url": f"{domain}?id=20230322085808_ff1bcf0d24ece3a37e3dac81b7e91733&language=EN",
                    "version": "1.07",
                },
            ],
        },
    )
