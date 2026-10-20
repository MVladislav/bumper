"""Tests for bumper/utils/map_image.py"""

import json
from pathlib import Path

from bumper.utils import map_image

# A map the robot uploaded, with the compressed parts still compressed.
STORED_MAP = Path(__file__).parent / "stored_map.json"


def _picture() -> bytes:
    """Return the picture of the stored map."""
    document = json.loads(STORED_MAP.read_text())
    return map_image.render_map(document)


def test_render_map() -> None:
    """The map is a picture the app can show."""
    picture = _picture()

    assert picture.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(picture) > 100


def test_the_picture_is_turned_a_quarter_turn() -> None:
    """The map the robot uploads is turned clockwise, like the app does it."""
    document = json.loads(STORED_MAP.read_text())
    image = map_image.build_map(document)

    assert image is not None
    # The room of the map is wider than it is high, the picture the other way.
    assert image.height > image.width
    assert image.width < 800


def test_the_picture_holds_the_palette_of_the_map() -> None:
    """The picture holds the colours of the map."""
    picture = _picture()

    # The palette of the picture holds one colour for every kind of cell.
    palette = picture[picture.index(b"PLTE") + 4 :]
    colours = {tuple(palette[index : index + 3]) for index in range(0, len(palette), 3)}
    assert map_image.PALETTE[1] in colours
    assert map_image.PALETTE[2] in colours


def test_the_rooms_get_a_colour_of_the_palette() -> None:
    """A room of the map is drawn with one of the room colours."""
    assert map_image._palette_index(1) == 1
    assert map_image._palette_index(2) == 2
    # Newer robots give every room a number of its own.
    assert map_image._palette_index(6) == 6
    assert map_image._palette_index(101) == 11
    assert map_image._palette_index(112) == 10


def test_render_map_without_a_grid() -> None:
    """A map without a grid has no picture."""
    assert map_image.render_map({"majorMap": {}}) == b""


def test_render_map_of_an_empty_room() -> None:
    """A map without anything on it has no picture."""
    assert map_image.render_map({"majorMap": {}, "minorMap": {}}) == b""
