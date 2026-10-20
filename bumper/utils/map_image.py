"""Render the map of a finished job as a picture.

The robot uploads the map of a finished job as a grid of cells, one byte per
cell. Every byte is an index into the palette of the map: the floor, the
walls, the carpet, the space that was not scanned and the rooms of the house.

The grid the robot uploads is turned a quarter turn clockwise to get the
picture, the same way the official app and the Home Assistant client draw it.
"""

from dataclasses import dataclass
import itertools
import struct
from typing import Any
import zlib

from bumper.utils import map_doc

# The palette of the map. The first entry is transparent, the rest are opaque.
PALETTE: tuple[tuple[int, int, int], ...] = (
    (0x00, 0x00, 0x00),  # transparent
    (0xBA, 0xDA, 0xFF),  # floor
    (0x4E, 0x96, 0xE2),  # wall
    (0x1A, 0x81, 0xED),  # carpet
    (0xDE, 0xE9, 0xFB),  # not scanned space
    (0xED, 0xF3, 0xFB),  # possible obstacle
    (0xA2, 0xBC, 0xE7),  # room 0
    (0xEC, 0xD0, 0x99),  # room 1
    (0x9B, 0xD4, 0xDA),  # room 2
    (0xEC, 0xC6, 0xC9),  # room 3
    (0xD7, 0xBC, 0xE3),  # room 4
    (0xC3, 0xE2, 0xB6),  # room 5
    (0x66, 0x66, 0x66),  # the outline of the house
    (0xF0, 0x00, 0x00),  # a virtual wall
    (0xFF, 0xA5, 0x00),  # a wall without mopping
)

# The number of colours that are not a room.
PALETTE_WITHOUT_ROOMS = 6

# The number of rooms the palette holds.
PALETTE_ROOMS = 6

# The value that means the cell is not part of the map.
TRANSPARENT = 0

# The palette index of the outline of the house.
OUTLINE = 12

# The palette index of a virtual wall.
VIRTUAL_WALL = 13

# The palette index of a wall without mopping.
MOPPING_WALL = 14

# The kinds of the lines in the profile of the map.
PROFILE_LINES = {"1": OUTLINE, "2": VIRTUAL_WALL, "3": MOPPING_WALL}


@dataclass(frozen=True)
class MapImage:
    """A picture of a map."""

    width: int
    height: int
    pixels: bytes

    def to_png(self) -> bytes:
        """Return the picture as a PNG image."""
        raw = b"".join(b"\x00" + self.pixels[row * self.width : (row + 1) * self.width] for row in range(self.height))

        return (
            b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 3, 0, 0, 0))
            + _chunk(b"PLTE", b"".join(bytes(colour) for colour in PALETTE))
            + _chunk(b"tRNS", bytes([0] + [255] * (len(PALETTE) - 1)))
            + _chunk(b"IDAT", zlib.compress(raw, 9))
            + _chunk(b"IEND", b"")
        )


def render_map(map_data: dict[str, Any]) -> bytes:
    """Return the map of a finished job as a PNG image."""
    image = build_map(map_data)
    if image is None:
        return b""
    return image.to_png()


def build_map(map_data: dict[str, Any]) -> MapImage | None:
    """Return the map of a finished job as a picture of palette indexes."""
    grid = map_doc.decode_grid(map_data)
    if not grid:
        return None

    row_grid, column_grid, row_piece, column_piece = map_doc.map_dimensions(map_data)
    width = column_grid * column_piece
    height = row_grid * row_piece
    if not width or not height or len(grid) < width * height:
        return None

    # The grid the robot uploads is turned a quarter turn clockwise.
    turned = bytearray(width * height)
    for row in range(height):
        for column in range(width):
            turned[(width - 1 - column) * height + row] = grid[row * width + column]

    indexes = bytes(_palette_index(value) for value in turned)

    bounds = _bounds(indexes, width, height)
    if bounds is None:
        return None
    left, top, right, bottom = bounds

    cropped = bytearray()
    for row in range(top, bottom):
        cropped += indexes[row * width + left : row * width + right]

    # The lines of the house are drawn over the cells.
    for x, y, colour in _outline(map_data, width):
        column = x - left
        row = y - top
        if 0 <= column < right - left and 0 <= row < bottom - top:
            cropped[row * (right - left) + column] = colour

    return MapImage(width=right - left, height=bottom - top, pixels=bytes(cropped))


def _outline(map_data: dict[str, Any], width: int) -> list[tuple[int, int, int]]:
    """Return the cells the lines of the house run through."""
    profile = map_doc.decode_profile(map_data)
    if not isinstance(profile, list):
        return []

    pixel = map_doc.map_pixel(map_data)
    offset = width // 2
    cells: list[tuple[int, int, int]] = []

    for entry in profile:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        colour = PROFILE_LINES.get(str(entry[0]))
        if colour is None:
            continue
        points: list[tuple[float, float, bool]] = []
        for part in str(entry[1]).split(";"):
            fields = part.strip().split(",")
            if len(fields) < 2:
                continue
            try:
                x = float(fields[0])
                y = float(fields[1])
            except ValueError:
                continue
            # A point that is not connected ends the line.
            points.append((x, y, len(fields) < 3 or fields[2].strip() != "3-1-0"))

        for (x1, y1, connected1), (x2, y2, _) in itertools.pairwise(points):
            if not connected1:
                continue
            cells.extend(
                (x, y, colour)
                for x, y in _line(
                    (x1 / pixel + offset, -y1 / pixel + offset),
                    (x2 / pixel + offset, -y2 / pixel + offset),
                )
            )
    return cells


def _line(start: tuple[float, float], end: tuple[float, float]) -> list[tuple[int, int]]:
    """Return the cells a line runs through."""
    x1, y1 = start
    x2, y2 = end
    cells: list[tuple[int, int]] = []
    steps = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
    for step in range(steps + 1):
        x = x1 + (x2 - x1) * step / steps
        y = y1 + (y2 - y1) * step / steps
        cells.append((round(x), round(y)))
    return cells


def _palette_index(value: int) -> int:
    """Return the palette index of a cell of the map."""
    if value > PALETTE_WITHOUT_ROOMS:
        return (value % PALETTE_ROOMS) + PALETTE_WITHOUT_ROOMS
    return value


def _bounds(indexes: bytes, width: int, height: int) -> tuple[int, int, int, int] | None:
    """Return the part of the map that holds something."""
    left = width
    top = height
    right = 0
    bottom = 0
    for row in range(height):
        line = indexes[row * width : (row + 1) * width]
        if TRANSPARENT not in line:
            continue
        filled = line.strip(bytes([TRANSPARENT]))
        if not filled:
            continue
        first = len(line) - len(line.lstrip(bytes([TRANSPARENT])))
        left = min(left, first)
        right = max(right, first + len(filled))
        top = min(top, row)
        bottom = max(bottom, row + 1)
    if bottom <= top:
        return None
    return left, top, right, bottom


def _chunk(tag: bytes, data: bytes) -> bytes:
    """Return a chunk of a PNG image."""
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
