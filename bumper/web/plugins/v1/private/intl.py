"""Intl plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPInternalServerError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.db import user_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.plugins import WebserverPlugin
from bumper.web.response_utils import response_success_v1

from . import BASE_URL

_LOGGER = logging.getLogger(__name__)


class IntlPlugin(WebserverPlugin):
    """Intl plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route("*", f"{BASE_URL}intl/member/basicInfo", _handle_basic_info),
            web.route("*", f"{BASE_URL}intl/member/signStatus", _handle_sign_status),
        ]


async def _handle_basic_info(request: Request) -> Response:
    """Get basic info."""
    try:
        user_dev_id = request.match_info.get("devid", "")
        user = user_repo.get_by_device_id(user_dev_id)
        if user is None:
            _LOGGER.warning(f"No user found for {user_dev_id}")
        else:
            frozen_integral_desc = "The points will be credited to your member account 20 days after the payment of the order."

            return response_success_v1(
                {
                    "availableGeneralIntegral": 9999,
                    "availableLimitedIntegral": 0,
                    "benefitList": [],
                    "expiringLimitedPointExplain": None,
                    "expiringLimitedPointShowDesc": None,
                    "expiringLimitedPoints": None,
                    "expiringPointDesc": None,
                    "expiringPointExplain": None,
                    "expiringPoints": None,
                    "frozenIntegral": 0,
                    "frozenIntegralDesc": frozen_integral_desc,
                    "goodsDetailIntegralDesc": "Redeem points for discounts!",
                    "integral": 9999,
                    "integralDescWapUrl": f"https://{bumper_isc.DOMAIN_SEC3}/web/page?no=jusapxaw",
                    "isCountryOpen": "Y",
                    "isLimitedIntegralOpen": "N",
                    "isMember": "Y",
                    "level": 1,
                    "levelIconUrl": f"https://{bumper_isc.DOMAIN_SEC2}/public/221027/f187b4b72f434fcc9eae655dbb389ac7.png",
                    "levelName": "VIP1",
                    "memberDescWapUrl": f"https://{bumper_isc.DOMAIN_SEC4}/DE/EN/content/description",
                    "remainingDay": None,
                    "shoppingGetIntegralShowDesc": None,
                    "shoppingGetIntegraltimes": None,
                    "shoppingGetIntegraltimesShowDesc": None,
                    "shoppingGetIntegraltimesUp": None,
                    "shoppingGetIntegraltimesUpShowDesc": None,
                    "signStatus": "SIGN",
                    "userHeadImg": None,
                    "userShowName": user.username,
                },
            )
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handling request"))
    raise HTTPInternalServerError


async def _handle_sign_status(_: Request) -> Response:
    """Sign. status."""
    return response_success_v1({"signStatus": "SIGN"})
