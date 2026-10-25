"""The guide pages of the Goat setup.

The app opens these pages in a web view when the user asks for help with the
setup of a mower. They are plain documents, in the same style as the agreement
page.
"""

from aiohttp import web

from bumper.web.agreement import document_page

_GUIDES: dict[str, tuple[str, str]] = {
    "set_pin_code_guide": (
        "Set a PIN code",
        """
        <h2>Set a PIN code</h2>
        <p>A PIN code protects the mower from being started by someone else.</p>
        <p>Open the robot panel in the app and follow the steps there to set the code.</p>
        """,
    ),
    "advanced_features": (
        "Bluetooth features",
        """
        <h2>Bluetooth features</h2>
        <p>The advanced Bluetooth features are part of the robot panel in the app.</p>
        <p>Open the robot panel while the phone is close to the mower and follow the steps there.</p>
        """,
    ),
    "winter_guide": (
        "Winter guide",
        """
        <h2>Winter guide</h2>
        <p>Before the mower is stored for the winter, clean it, charge it and keep it in a dry place.</p>
        <p>Open the robot panel in the app and follow the steps for the end of the season.</p>
        """,
    ),
    "pin_code_settings": (
        "PIN code settings",
        """
        <h2>PIN code settings</h2>
        <p>The PIN code of the mower is set in the robot panel of the app.</p>
        <p>Keep the code somewhere safe; it is needed when the mower is started.</p>
        """,
    ),
    "rtk_install_method": (
        "Install the RTK station",
        """
        <h2>Install the RTK station</h2>
        <p>The RTK station needs a clear view of the sky and a stable place to stand.</p>
        <p>Place it outside and follow the steps in the robot panel of the app to finish the setup.</p>
        """,
    ),
    "maintenance_guide_o_series": (
        "Maintenance guide",
        """
        <h2>Maintenance guide</h2>
        <p>Clean the blades, check the wheels and keep the charging contacts dry.</p>
        <p>Open the robot panel in the app and follow the steps for the O series.</p>
        """,
    ),
}


def goat_page(guide: str) -> web.Response:
    """Return one guide page of the Goat setup."""
    title, body = _GUIDES[guide]
    return web.Response(
        text=document_page(title, body),
        content_type="text/html",
        charset="utf-8",
        headers={
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "expires": "Thu, 01 Jan 1970 00:00:00 GMT",
        },
    )
