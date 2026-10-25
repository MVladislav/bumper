"""Tests for bumper/web/hosts.py"""

from bumper.web.hosts import photo_url, placeholder_photo_url


def test_photo_url_is_the_svg_picture() -> None:
    """The app receives the SVG form of the map."""
    url = photo_url("api-app.ecouser.net", "photo_1")

    assert url == "https://api-app.ecouser.net/api/photo/download?id=photo_1&format=svg"


def test_the_placeholder_url_has_no_id() -> None:
    """The shared placeholder is asked for without a stored photo."""
    url = placeholder_photo_url("api-app.ecouser.net")

    assert url == "https://api-app.ecouser.net/api/photo/download?format=svg"
