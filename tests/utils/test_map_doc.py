"""Tests for bumper/utils/map_doc.py"""

import base64
import json
import lzma
from pathlib import Path

from bumper.utils import map_doc

# A map the robot uploaded, with the compressed parts still compressed.
MAP_DOCUMENT = {
    "mid": "1999531095",
    "majorMap": {
        "cellHeight": 8,
        "cellWidth": 8,
        "mapCount": 6,
        "mapEncode": "7z",
        "pieceHeight": 8,
        "pieceWidth": 8,
        "pixel": 50,
        "value": "1295764014,1295764014,1295764014",
    },
    "mapTrace": {"pointCount": 2, "tid": 1709547294, "totalCount": 2, "traceStart": 0, "traceValue": ""},
}


def _encode_7z(payload: bytes) -> str:
    """Encode a payload the way the robot does."""
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE)
    # The robot writes the size with four bytes instead of eight.
    short = compressed[:5] + len(payload).to_bytes(4, "little") + compressed[13:]
    return base64.b64encode(short).decode("ascii")


def test_decode_7z_round_trip() -> None:
    """The payload is the LZMA format with a four byte size."""
    payload = bytes(range(256)) * 4
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE)
    # Put the size back as the short form the robot writes.
    short = compressed[:5] + len(payload).to_bytes(4, "little") + compressed[13:]

    assert map_doc.decode_7z(short) == payload
    assert _encode_7z(payload) == base64.b64encode(short).decode("ascii")


def test_encode_7z_round_trip() -> None:
    """An encoded payload is read back the same way."""
    payload = bytes(range(256)) * 4

    encoded = map_doc.encode_7z(payload)

    assert map_doc.decode_7z(base64.b64decode(encoded)) == payload


def test_encode_7z_header() -> None:
    """The app only accepts a payload with the dictionary size of the format."""
    encoded = base64.b64decode(map_doc.encode_7z(b"payload"))

    assert encoded[:5] == bytes([0x5D, 0x00, 0x00, 0x04, 0x00])
    assert int.from_bytes(encoded[1:5], "little") == 262144
    assert int.from_bytes(encoded[5:9], "little") == len(b"payload")


def test_decode_grid() -> None:
    """The grid is one byte per cell."""
    grid = bytes(range(256)) * 16
    document = {
        **MAP_DOCUMENT,
        "minorMap": {"value": _encode_7z(grid)},
    }

    assert map_doc.decode_grid(document) == grid


def test_decode_grid_without_a_payload() -> None:
    """A map without a grid decodes to nothing."""
    assert map_doc.decode_grid(MAP_DOCUMENT) == b""


def test_decode_trace() -> None:
    """A trace point is a y and a x coordinate and a flag byte."""
    trace = b"".join(
        [
            (2).to_bytes(2, "little", signed=True),
            (-2).to_bytes(2, "little", signed=True),
            b"\x01",
            (5).to_bytes(2, "little", signed=True),
            (3).to_bytes(2, "little", signed=True),
            b"\x81",
        ],
    )
    document = {**MAP_DOCUMENT, "mapTrace": {**MAP_DOCUMENT["mapTrace"], "traceValue": _encode_7z(trace)}}

    assert map_doc.decode_trace(document) == trace


def test_map_pieces() -> None:
    """The grid is split into the pieces the app puts back together."""
    # The map is 8 x 8 pieces of 8 x 8 cells, so 64 x 64 cells.
    grid = bytes(range(256)) * 16
    document = {
        **MAP_DOCUMENT,
        "minorMap": {"value": _encode_7z(grid)},
    }

    pieces = map_doc.map_pieces(document)

    assert len(pieces) == 64
    # Every piece holds a grid of cells, one row after the other.
    # A piece holds the first rows of the grid, eight cells of every row.
    expected = b"".join(grid[row * 64 : row * 64 + 8] for row in range(8))
    first = map_doc.decode_7z(base64.b64decode(pieces["0"]))
    assert len(first) == 64
    assert first == expected
    # The second piece is the next block of cells of the same rows.
    expected = b"".join(grid[row * 64 + 8 : row * 64 + 16] for row in range(8))
    second = map_doc.decode_7z(base64.b64decode(pieces["1"]))
    assert second == expected


def test_map_pieces_without_a_payload() -> None:
    """A map without a grid has no pieces."""
    assert map_doc.map_pieces(MAP_DOCUMENT) == {}


def test_map_pieces_of_a_map_without_a_grid() -> None:
    """A map without a grid size has no pieces."""
    document = {**MAP_DOCUMENT, "majorMap": {}, "minorMap": {"value": _encode_7z(bytes(64))}}

    assert map_doc.map_pieces(document) == {}


def test_trace_pieces() -> None:
    """The driven path is kept the way the app reads it."""
    trace = (1).to_bytes(2, "little", signed=True) + (2).to_bytes(2, "little", signed=True) + b"\x01"
    document = {**MAP_DOCUMENT, "mapTrace": {**MAP_DOCUMENT["mapTrace"], "traceValue": _encode_7z(trace)}}

    pieces = map_doc.trace_pieces(document)

    assert list(pieces) == ["1709547294"]
    assert map_doc.decode_7z(base64.b64decode(pieces["1709547294"])) == trace


def test_trace_pieces_without_a_payload() -> None:
    """A map without a driven path has no trace."""
    assert map_doc.trace_pieces(MAP_DOCUMENT) == {}


def test_cleaned_map() -> None:
    """The map of a finished job holds the pieces and the driven path."""
    grid = bytes(range(256)) * 16
    document = {
        **MAP_DOCUMENT,
        "minorMap": {"value": _encode_7z(grid)},
    }

    cleaned = map_doc.cleaned_map(document)

    assert set(cleaned) == {"map", "trace"}
    assert len(cleaned["map"]) == 64


def test_cleaned_map_without_a_map() -> None:
    """A job without a map has no pieces."""
    assert map_doc.cleaned_map(None) == {"map": {}, "trace": {}}


def test_the_stored_map_is_split_into_pieces() -> None:
    """A map the robot uploaded is split into the pieces the app expects."""
    document = json.loads((Path(__file__).parent / "stored_map.json").read_text())

    pieces = map_doc.map_pieces(document)

    assert len(pieces) == 64
    # Every piece holds a grid of 100 x 100 cells.
    first = map_doc.decode_7z(base64.b64decode(pieces["0"]))
    assert len(first) == 10000
    # The pieces are the blocks of the grid of the upload.
    grid = map_doc.decode_grid(document)
    expected = b"".join(grid[row * 800 : row * 800 + 100] for row in range(100))
    assert first == expected


def test_the_stored_map_keeps_its_driven_path() -> None:
    """A map the robot uploaded keeps the driven path it came with."""
    document = json.loads((Path(__file__).parent / "stored_map.json").read_text())

    trace = map_doc.decode_trace(document)

    # Every point of the path is five bytes.
    assert len(trace) == document["mapTrace"]["pointCount"] * 5


def test_the_app_puts_the_pieces_back_together() -> None:
    """The pieces hold the grid of the upload, the way the app reads them."""
    document = json.loads((Path(__file__).parent / "stored_map.json").read_text())
    pieces = map_doc.map_pieces(document)

    # The app builds a map of 100 by 100 pieces of 8 by 8 cells.
    row_grid, column_grid, row_piece, column_piece = 100, 100, 8, 8
    width = column_grid * column_piece
    height = row_grid * row_piece
    buffer = [[0] * width for _ in range(height)]

    for key, value in pieces.items():
        data = map_doc.decode_7z(base64.b64decode(value))
        piece = int(key)
        piece_row = piece // column_piece
        piece_column = piece % column_piece
        offset = 0
        for row in range(row_grid):
            for column in range(column_grid):
                buffer[row + piece_row * row_grid][column + piece_column * column_grid] = data[offset]
                offset += 1

    rebuilt = bytes(cell for row in buffer for cell in row)
    assert rebuilt == map_doc.decode_grid(document)
