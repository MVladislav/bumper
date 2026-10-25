"""Web page plugin module.

The app asks for a page that Bumper does not ship, so the answer is a
short page that says so.
"""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bumper.utils.settings import config as bumper_isc

from . import PREFIX

#: The style of the page. The web view of the app is a phone, so the page
#: is written for the width of a phone.
_STYLE = """
    body {
      font-family: Arial, sans-serif;
      margin: 2rem auto;
      padding: 1em;
      max-width: 52rem;
      font-size: 1rem;
      line-height: 1.5;
    }
    h2 { text-align: center; }
    p { text-align: center; }
    code {
      font-size: 1.25rem;
      font-weight: bold;
    }
"""


def get_web_page() -> str:
    """Return the page the app asks for that Bumper does not ship."""
    return f"""<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1, maximum-scale=1.0, user-scalable=no"/>
<title>Bumper</title>
<style>{_STYLE}</style>
</head>

<body>
<h2>Bumper says hi 👋</h2>
<p style="font-style: italic;">
    This page is a feature that Bumper does not ship. We are a self-hosted
    cloud replacement, not a cloud. The verification code never left the
    building, because the building has no mailbox.
</p>
<h2>Need the verification code?</h2>
<p>
    Nice, you found it. Use <code>{bumper_isc.EMAIL_VERIFY_CODE}</code> on the
    previous screen: Bumper accepts it every time. There is no mailbox, so
    there is no other code to wait for.
</p>
<p>
    <a href="https://github.com/MVladislav/bumper">Read the docs instead.</a>
</p>
</body>

</html>
"""


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/page")
async def _handle_web_page(_: Request) -> Response:
    """Handle web page."""
    return web.Response(text=get_web_page(), content_type="text/html", charset="utf-8")
