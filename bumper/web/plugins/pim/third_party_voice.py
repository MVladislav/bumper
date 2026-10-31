"""Third party voice control plugin module.

The app asks for a page that Bumper does not ship, so the answer is a
short page that says so.
"""

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

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
"""


def get_third_party_voice_control() -> str:
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
    Third-party voice control is a cloud feature. Bumper is a LAN. The two
    have never met, and we would like to keep it that way.
</p>
</body>

</html>
"""


routes = web.RouteTableDef()


@routes.view(f"{PREFIX}/third_party_voice_control.html")
async def _handle_third_party_voice_control(_: Request) -> Response:
    """Handle third party voice control."""
    return web.Response(text=get_third_party_voice_control(), content_type="text/html", charset="utf-8")
