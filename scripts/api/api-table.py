#!/usr/bin/env python3
"""Print the route table of the Ecovacs API with the shape of every endpoint.

The route table is the source of truth: the url of an endpoint and the shape
it answers with are both written down where the endpoint is. This script
reads it, so the table can be reviewed, diffed and checked against the
captured traffic.

    ./scripts/api/api-table.py            # the table
    ./scripts/api/api-table.py --json     # as json, for a diff
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[2]))

from bumper.web import plugins  # noqa: E402
from bumper.web.envelope import describe  # noqa: E402


def collect() -> list[dict[str, Any]]:
    """Return every route with the shape it answers with."""
    rows: list[dict[str, Any]] = []
    for module in plugins.plugin_modules():
        table = getattr(module, "routes", None)
        if table is None:
            continue
        for route in table:
            handler = getattr(route, "handler", None)
            rows.append(
                {
                    "method": route.method,
                    "path": route.path,
                    "shape": _shape_of(handler),
                    "module": module.__name__,
                },
            )
    return sorted(rows, key=lambda row: (row["path"], row["method"]))


def _shape_of(handler: Any) -> str:
    """Return a readable name of the shape a handler answers with.

    An endpoint that answers in one shape per operation holds a table of
    them; the table is what names the shapes.
    """
    operations = getattr(handler, "operations", None)
    if operations:
        return ", ".join(f"{name}: {describe(operation.template)}" for name, operation in operations.items())

    return describe(getattr(handler, "template", None))


def main() -> None:
    """Print the table."""
    rows = collect()
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
        return

    width = max((len(row["path"]) for row in rows), default=10)
    for row in rows:
        print(f"{row['method']:6} {row['path']:<{width}}  {row['shape']}")
    print(f"\n{len(rows)} routes")


if __name__ == "__main__":
    main()
