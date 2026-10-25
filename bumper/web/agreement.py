"""The agreement page of the app.

The app shows the user agreement and the privacy policy in a web view. The
page comes from the server of the agreement, so the shape of the answer is
the one the web view expects: a whole document, not a piece of one.
"""

from aiohttp import web
from aiohttp.web_request import Request

_AGREEMENT = """
    <h2 style="text-align: center;">Welcome to Bumper 🚗💨</h2>
    <p><strong>Mini User-ish Agreement</strong></p>
    <ul>
      <li>
          <strong>You break it, you fix it.</strong>
          We built it, you run it. If it breaks, blame your last caffeine-fueled update.
      </li>
      <li>
          <strong>Your data is yours.</strong>
          We can't see it. We don't want it. Bumper runs at home. It's antisocial like that.
      </li>
      <li>
          <strong>No cloud, no cry.</strong>
          If things go wrong, check your Wi-Fi, cat, or moon phase. Probably not our fault.
      </li>
      <li>
          <strong>Support not included.</strong>
          Ask your future self or consult the ancient scrolls (aka README.md).
      </li>
      <li>
          <strong>No evil bots.</strong>
          Don't use Bumper for villainy. Floors, yes. World domination, no.
      </li>
    </ul>
    <p style="text-align: center; font-style: italic;">
      By using Bumper, you accept responsibility and the eternal right to brag about your local setup. 🍕
    </p>
"""

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
    li { margin-bottom: 0.5em; }
"""


def document_page(title: str, body: str, language: str = "en") -> str:
    """Return a document page in the style of the pages the app shows."""
    return f"""<!DOCTYPE html>
<html lang="{language.lower()}">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1, maximum-scale=1.0, user-scalable=no"/>
<title>{title}</title>
<style>{_STYLE}</style>
</head>

<body>
{body}
</body>

</html>
"""


def agreement_page(language: str) -> str:
    """Return the page of the agreement."""
    return document_page("Bumper", _AGREEMENT, language)


async def handle_content_agreement(request: Request) -> web.Response:
    """Content Agreement (/content/agreement)."""
    language = request.query.get("language", "EN")

    return web.Response(
        text=agreement_page(language),
        content_type="text/html",
        charset="utf-8",
        headers={
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "expires": "Thu, 01 Jan 1970 00:00:00 GMT",
            "content-language": language.lower(),
        },
    )
