"""Offline plugin module."""

from collections.abc import Iterable
import logging

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp.web_routedef import AbstractRouteDef

from bumper.web.plugins import WebserverPlugin

_LOGGER = logging.getLogger(__name__)


class OfflinePlugin(WebserverPlugin):
    """Offline plugin."""

    @property
    def routes(self) -> Iterable[AbstractRouteDef]:
        """Plugin routes."""
        return [
            web.route(
                "*",
                "/offline.html",
                _handle_offline,
            ),
        ]


async def _handle_offline(_: Request) -> Response:
    """Handle Offline."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Bumper is Offline</title>
    <style>
        body {
        background-color: #f4f4f4;
        font-family: Arial, sans-serif;
        color: #333;
        text-align: center;
        padding: 2em;
        }

        .offline-box {
        background-color: #fff;
        padding: 2em;
        border-radius: 12px;
        max-width: 52rem;
        margin: 2rem auto;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        }

        h1 {
        font-size: 24px;
        color: #b00020;
        }

        p {
        margin: 1em 0;
        font-size: 16px;
        }

        .emoji {
        font-size: 40px;
        margin: 0.5em 0;
        }

        .hint {
        font-size: 14px;
        color: #666;
        margin-top: 2em;
        font-style: italic;
        }
    </style>
    </head>
    <body>
    <div class="offline-box">
        <div class="emoji">🤖🔌</div>
        <h1>Bumper is Currently Offline</h1>
        <p>It's either napping, charging, or having a deep existential crisis.</p>
        <p>Check its power, Wi-Fi, or whisper words of encouragement.</p>
        <p>We'll reconnect once it remembers how to be a robot again.</p>
        <div class="hint">Tip: Turning it off and on again is 87% effective.</div>
    </div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")
