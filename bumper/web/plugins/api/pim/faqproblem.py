"""Pim FAQ problem plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin
from bumper.web.static_api import get_faq_problem

_LOGGER = logging.getLogger(__name__)


class FaqProblemPlugin(WebserverPlugin):
    """FAQ problem plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                "/faqproblem.html",
                _handle_faq_problem,
            ),
        ]


async def _handle_faq_problem(_: Request) -> Response:
    """Handle FAQ problem."""
    return web.Response(text=get_faq_problem(), content_type="text/html")
