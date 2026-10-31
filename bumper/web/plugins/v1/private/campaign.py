"""Campaign plugin module."""

from datetime import datetime, timedelta
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.envelope import GL_V1, bind

from . import BASE_URL

routes = web.RouteTableDef()


@routes.view(f"{BASE_URL}campaign/homePageAlert")
@bind(GL_V1)
async def _handle_home_page_alert(_: Request) -> Any:
    """Homepage alert."""
    return {
        "clickSchemeUrl": None,
        "clickWebUrl": None,
        "hasCampaign": "N",
        "imageUrl": None,
        "nextAlertTime": utils.convert_to_millis(
            (datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(hours=12)).timestamp(),
        ),
        "serverTime": utils.get_current_time_as_millis(),
    }
