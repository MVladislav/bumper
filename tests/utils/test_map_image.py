"""Tests for bumper/utils/map_image.py"""

import json
from pathlib import Path
import struct

import pytest

from bumper.utils import map_doc, map_image

# A map the robot uploaded, with the compressed parts still compressed.
STORED_MAP = Path(__file__).parent / "stored_map.json"


@pytest.mark.timeout(30)
def test_render_map_svg() -> None:
    """The same picture is available as a vector image for the web view."""
    document = json.loads(STORED_MAP.read_text())
    image = map_image.render_map_svg(document)

    assert image.startswith(b"<svg ")
    assert b"</svg>" in image
    assert b'shape-rendering="crispEdges"' in image

    raster = map_image.build_map(document)
    assert raster is not None
    assert map_image.PATH in raster.pixels


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
    document = json.loads(STORED_MAP.read_text())
    picture = map_image.render_map_svg(document)

    # The picture holds one colour for every kind of cell it draws.
    assert b"#badaff" in picture
    assert b"#4e96e2" in picture


def test_the_path_is_drawn_on_the_map() -> None:
    """Trace points land in the map area and disconnected segments stay separate."""
    document = json.loads(STORED_MAP.read_text())
    image = map_image.build_map(document)

    assert image is not None
    path_pixels = image.pixels.count(map_image.PATH)
    assert path_pixels > 0
    assert path_pixels < image.width * image.height


def test_trace_coordinates_are_scaled_and_disconnected_points_start_new_segments() -> None:
    """The trace uses 10 mm coordinates and its flag controls line breaks."""

    def point(x: int, y: int, flags: int) -> bytes:
        source_row = (x - 400) * 5
        source_column = (400 - y) * 5
        return struct.pack("<hhB", source_row, source_column, flags)

    trace = point(300, 300, 1) + point(300, 310, 0x81) + point(310, 310, 1)
    map_data = {
        "majorMap": {"pixel": 50},
        "mapTrace": {"traceValue": map_doc.encode_7z(trace)},
    }

    cells = set(map_image._path(map_data, 800, 800))

    assert (300, 300) not in cells
    assert {(row, 310) for row in range(300, 311)} <= cells


def test_the_rooms_get_a_colour_of_the_palette() -> None:
    """A room of the map is drawn with one of the room colours."""
    assert map_image._palette_index(1) == 1
    assert map_image._palette_index(2) == 2
    # Newer robots give every room a number of its own.
    assert map_image._palette_index(6) == 6
    assert map_image._palette_index(101) == 11
    assert map_image._palette_index(112) == 10


def test_a_map_without_transparent_cells_is_a_picture() -> None:
    """A map that fills every cell is drawn like any other map."""
    grid = bytes([1]) * 64 * 64
    document = {
        "majorMap": {"cellHeight": 8, "cellWidth": 8, "pieceHeight": 8, "pieceWidth": 8, "pixel": 50},
        "minorMap": {"value": map_doc.encode_7z(grid)},
    }

    raster = map_image.build_map(document)

    assert raster is not None
    assert (raster.width, raster.height) == (64, 64)
    assert set(raster.pixels) == {1}


def test_render_map_without_a_grid() -> None:
    """A map without a grid has no picture."""
    assert map_image.render_map_svg({"majorMap": {}}) == b""


def test_render_map_of_an_empty_room() -> None:
    """A map without anything on it has no picture."""
    assert map_image.render_map_svg({"majorMap": {}, "minorMap": {}}) == b""
