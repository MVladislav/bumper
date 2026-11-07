"""Tests for safe, deterministic response-shape fixture updates."""

import importlib.util
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).parents[1] / "scripts/api/2-extract-response-shapes.py"
SPEC = importlib.util.spec_from_file_location("response_shape_extractor", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
EXTRACTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXTRACTOR)


def test_merge_shapes_keeps_old_variants_and_adds_new_ones() -> None:
    """A partial capture must not remove previously recorded shapes."""
    old: dict[str, dict[str, list[dict[str, str]]]] = {
        "/api/example": {"GET": [{"code": "int", "data": "dict"}]},
        "/api/old": {"POST": [{"ret": "str"}]},
    }
    new: dict[str, dict[str, list[dict[str, str]]]] = {
        "/api/example": {
            "GET": [
                {"code": "int", "data": "dict"},
                {"code": "int", "message": "str"},
            ],
        },
        "/api/new": {"POST": [{"ret": "str"}]},
    }

    result = EXTRACTOR.merge_shapes(old, new)

    assert result["/api/old"] == old["/api/old"]
    assert result["/api/new"] == new["/api/new"]
    assert len(result["/api/example"]["GET"]) == 2


def test_merge_shapes_orders_endpoints_methods_and_variants() -> None:
    """The same observations produce stable JSON ordering."""
    shapes: dict[str, Any] = {
        "/z": {"POST": [{"b": "str"}, {"a": "int"}]},
        "/a": {"GET": [{"ok": "bool"}]},
    }

    result = EXTRACTOR.merge_shapes({}, shapes)

    assert list(result) == ["/a", "/z"]
    assert result["/z"]["POST"] == [{"a": "int"}, {"b": "str"}]
