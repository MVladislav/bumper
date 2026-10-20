"""Decode the map document the robot uploads and serve it the way the app reads it.

The robot posts a JSON document with the map of a finished job. The map itself
is a grid of cells, one byte per cell, and it is compressed with the 7z format.
That format is the LZMA "alone" format with a four byte size instead of an eight
byte one.

The app asks the server for the map of a finished job and expects the pieces of
the grid and the driven path, both compressed the same way. The server splits
the grid into the pieces the app puts back together.
"""

import base64
import json
import lzma
import struct
from typing import Any

# The dictionary size the app expects in the header of a compressed payload.
DICT_SIZE = 262144

# The properties byte of the LZMA format with the default settings.
PROPERTIES = 0x5D


def decode_7z(data: bytes) -> bytes:
    """Decode a payload in the 7z format the robot uses."""
    header = data[:5] + data[5:9] + b"\x00\x00\x00\x00"
    return lzma.decompress(header + data[9:], format=lzma.FORMAT_ALONE)


def encode_7z(data: bytes) -> str:
    """Encode a payload in the 7z format the robot uses, as base64."""
    filters = [{"id": lzma.FILTER_LZMA1, "dict_size": DICT_SIZE}]
    stream = lzma.compress(data, format=lzma.FORMAT_RAW, filters=filters)
    header = bytes([PROPERTIES]) + struct.pack("<I", DICT_SIZE) + struct.pack("<I", len(data))
    return base64.b64encode(header + stream).decode("ascii")


def _decoded_field(map_data: dict[str, Any], section: str, field: str) -> bytes:
    """Return a decoded field of the map, or an empty result."""
    value = map_data.get(section, {})
    if not isinstance(value, dict):
        return b""
    raw = value.get(field)
    if not isinstance(raw, str) or not raw:
        return b""
    try:
        return decode_7z(base64.b64decode(raw))
    except (ValueError, lzma.LZMAError):
        return b""


def decode_grid(map_data: dict[str, Any]) -> bytes:
    """Return the cell grid of the map, one byte per cell."""
    return _decoded_field(map_data, "minorMap", "value")


def decode_profile(map_data: dict[str, Any]) -> Any:
    """Return the profile of the map, the outlines of the rooms."""
    profile = _decoded_field(map_data, "mapProfile", "value")
    if not profile:
        return None
    try:
        return json.loads(profile)
    except (ValueError, UnicodeDecodeError):
        return None


def decode_trace(map_data: dict[str, Any]) -> bytes:
    """Return the driven path of the map."""
    return _decoded_field(map_data, "mapTrace", "traceValue")


def map_dimensions(map_data: dict[str, Any]) -> tuple[int, int, int, int]:
    """Return the grid and the piece sizes of the map."""
    major = map_data.get("majorMap", {})
    if not isinstance(major, dict):
        return 0, 0, 0, 0
    return (
        _int(major, "pieceWidth"),
        _int(major, "pieceHeight"),
        _int(major, "cellWidth"),
        _int(major, "cellHeight"),
    )


def map_pieces(map_data: dict[str, Any]) -> dict[str, str]:
    """Return the pieces of the map, compressed the way the app expects them."""
    row_grid, column_grid, row_piece, column_piece = map_dimensions(map_data)
    if not all((row_grid, column_grid, row_piece, column_piece)):
        return {}

    grid = decode_grid(map_data)
    width = column_grid * column_piece
    height = row_grid * row_piece
    if len(grid) < width * height:
        return {}

    pieces: dict[str, str] = {}
    for piece in range(row_piece * column_piece):
        piece_row = piece // column_piece
        piece_column = piece % column_piece
        data = bytearray()
        for row in range(row_grid):
            offset = (piece_row * row_grid + row) * width + piece_column * column_grid
            data += grid[offset : offset + column_grid]
        pieces[str(piece)] = encode_7z(bytes(data))
    return pieces


def trace_pieces(map_data: dict[str, Any]) -> dict[str, str]:
    """Return the driven path of the map, compressed the way the app expects it."""
    trace = map_data.get("mapTrace", {})
    if not isinstance(trace, dict):
        return {}
    data = decode_trace(map_data)
    if not data:
        return {}
    return {str(_int(trace, "tid")): encode_7z(data)}


def cleaned_map(map_data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the map of a finished job the way the app reads it."""
    if not map_data:
        return {"map": {}, "trace": {}}
    return {"map": map_pieces(map_data), "trace": trace_pieces(map_data)}


def map_pixel(map_data: dict[str, Any]) -> int:
    """Return the size of a cell of the map in the units of the robot."""
    major = map_data.get("majorMap", {})
    if not isinstance(major, dict):
        return 50
    return _int(major, "pixel", 50)


def _int(data: dict[str, Any], key: str, default: int = 0) -> int:
    """Return an integer field of a document."""
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
