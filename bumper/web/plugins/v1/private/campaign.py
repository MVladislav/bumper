"""Campaign plugin module."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import get_success_response

from . import BASE_URL


class CampaignPlugin(WebserverPlugin):
    """Campaign plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                f"{BASE_URL}campaign/homePageAlert",
                _handle_home_page_alert,
            ),
        ]


async def _handle_home_page_alert(_: Request) -> Response:
    """Homepage alert."""
    return get_success_response(
        {
            "clickSchemeUrl": None,
            "clickWebUrl": None,
            "hasCampaign": "N",
            "imageUrl": None,
            "nextAlertTime": utils.convert_to_millis(
                (datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(hours=12)).timestamp(),
            ),
            "serverTime": utils.get_current_time_as_millis(),
        },
    )
