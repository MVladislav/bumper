"""Build the map fixture the tests use.

The map is a synthetic one: a room with two areas and a path through it, built
the way the robot builds it, so no real map of a real house ends up in the
repository.
"""

import base64
import json
import lzma
from pathlib import Path
import struct
import zlib

SIZE = 800
PIECE = 100
PIECES = 8
PIXEL = 50

# The room, in cells.
LEFT, TOP = 260, 300
RIGHT, BOTTOM = 540, 560

# The values of the cells, the same palette the app draws the map with.
TRANSPARENT = 0
FLOOR = 1
WALL = 2
NOT_SCANNED = 4
ROOM_A = 7
ROOM_B = 9


def encode_7z(payload: bytes) -> str:
    """Encode a payload the way the robot does."""
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE)
    short = compressed[:5] + len(payload).to_bytes(4, "little") + compressed[13:]
    return base64.b64encode(short).decode("ascii")


def build_grid() -> bytes:
    """Return the grid of the map."""
    grid = bytearray(SIZE * SIZE)
    for row in range(TOP, BOTTOM):
        for column in range(LEFT, RIGHT):
            grid[row * SIZE + column] = FLOOR
    # The walls of the room.
    for column in range(LEFT, RIGHT):
        grid[TOP * SIZE + column] = WALL
        grid[(BOTTOM - 1) * SIZE + column] = WALL
    for row in range(TOP, BOTTOM):
        grid[row * SIZE + LEFT] = WALL
        grid[row * SIZE + RIGHT - 1] = WALL
    # Two areas in the room.
    for row in range(TOP + 20, TOP + 120):
        for column in range(LEFT + 20, LEFT + 120):
            grid[row * SIZE + column] = ROOM_A
    for row in range(TOP + 150, TOP + 230):
        for column in range(LEFT + 150, LEFT + 250):
            grid[row * SIZE + column] = ROOM_B
    return bytes(grid)


def build_profile() -> list[list[str]]:
    """Return the outline of the house.

    The robot sends the outline in the space of the picture, so the corners of
    the room are turned into that space.
    """

    def point(row: int, column: int) -> str:
        x = (row - SIZE // 2) * PIXEL
        y = (column - SIZE // 2 + 1) * PIXEL
        return f"{x},{y},1"

    points = [
        point(TOP, LEFT),
        point(TOP, RIGHT - 1),
        point(BOTTOM - 1, RIGHT - 1),
        point(BOTTOM - 1, LEFT),
    ]
    return [["1", "0;" + ";".join(points)]]


def build_trace() -> bytes:
    """Return the path through the room, five bytes per point."""
    trace = bytearray()
    for step in range(150):
        row = TOP + 30 + (step * 3) % 200
        column = LEFT + 30 + (step * 5) % 200
        trace += struct.pack("<hh", row - SIZE // 2, column - SIZE // 2)
        trace += bytes([1])
    return bytes(trace)


def build_manifest(grid: bytes) -> list[str]:
    """Return the checksum of every piece of the map."""
    checksums = []
    for piece in range(PIECES * PIECES):
        piece_row = piece // PIECES
        piece_column = piece % PIECES
        data = bytearray()
        for row in range(PIECE):
            offset = (piece_row * PIECE + row) * SIZE + piece_column * PIECE
            data += grid[offset : offset + PIECE]
        checksums.append(str(zlib.crc32(bytes(data))))
    return checksums


def main() -> None:
    """Write the map fixture."""
    grid = build_grid()
    document = {
        "mid": "1999531095",
        "majorMap": {
            "cellHeight": 8,
            "cellWidth": 8,
            "mapCount": 6,
            "mapEncode": "7z",
            "pieceHeight": PIECE,
            "pieceWidth": PIECE,
            "pixel": PIXEL,
            "value": ",".join(build_manifest(grid)),
        },
        "minorMap": {"value": encode_7z(grid)},
        "mapProfile": {
            "infoSize": 470,
            "value": encode_7z(json.dumps(build_profile()).encode()),
        },
        "mapTrace": {
            "pointCount": 150,
            "tid": "1709547294",
            "totalCount": 150,
            "traceStart": 0,
            "traceValue": encode_7z(build_trace()),
        },
    }
    path = Path(__file__).parent / "stored_map.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
