#!/usr/bin/env python3
"""Write the route and shape snapshots of the web server.

`tests/web/routes.txt` pins the method and url of every route, and
`tests/web/shapes.txt` pins the shape every route answers with. Both are read
by the test suite. This script builds the same application the server builds
and writes the snapshots from it, so a new endpoint does not need a hand edit.

    ./scripts/api/sync-route-snapshots.py           # write the snapshots
    ./scripts/api/sync-route-snapshots.py --check   # report drift, change nothing

The pre-commit hook runs the writing form when a file under `bumper/web/`
changes.
"""

import argparse
from collections.abc import Iterator
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[2]))

from bumper.web.envelope import describe  # noqa: E402
from bumper.web.server import WebServer, WebserverBinding  # noqa: E402

#: The repository, so the tool can be called from anywhere.
REPO_ROOT = Path(__file__).parents[2]
#: The snapshot of the urls.
ROUTES = REPO_ROOT / "tests/web/routes.txt"
#: The snapshot of the answer shapes.
SHAPES = REPO_ROOT / "tests/web/shapes.txt"


def _routes(router: Any) -> Iterator[tuple[str, Any]]:
    """Yield every route of a router and of the sub apps under it."""
    for resource in router.resources():
        info = resource.get_info()
        if (app := info.get("app")) is not None:
            yield from _routes(app.router)
            continue
        for route in resource:
            yield f"{route.method} {resource.canonical}", route.handler


def _shape_of(handler: Any) -> str:
    """Return the shape a handler answers with."""
    operations = getattr(handler, "operations", None)
    if operations:
        return ", ".join(f"{name}: {describe(operation.template)}" for name, operation in operations.items())
    return describe(getattr(handler, "template", None))


def _snapshots() -> tuple[list[str], list[str]]:
    """Return the route lines and the shape lines of the application."""
    server = WebServer(WebserverBinding("127.0.0.1", 8007, False), False)
    routes = list(_routes(server._app.router))
    return (
        sorted({path for path, _ in routes}),
        sorted({f"{path} {_shape_of(handler)}" for path, handler in routes}),
    )


def _lines(path: Path) -> list[str]:
    """Return the non-empty lines of a snapshot, or an empty list when it is missing."""
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    """Write the snapshots, or report the drift when --check is given."""
    parser = argparse.ArgumentParser(description="Write the route and shape snapshots of the web server.")
    parser.add_argument("--check", action="store_true", help="report drift and exit non-zero instead of writing")
    args = parser.parse_args()

    routes, shapes = _snapshots()
    changed = False

    for path, found in ((ROUTES, routes), (SHAPES, shapes)):
        expected = _lines(path)
        missing = sorted(set(expected) - set(found))
        added = sorted(set(found) - set(expected))
        if not missing and not added:
            if not args.check:
                print(f"{path.relative_to(REPO_ROOT)}: {len(found)} entries")
            continue

        changed = True
        print(f"{path.relative_to(REPO_ROOT)}:")
        for line in missing:
            print(f"  gone: {line}")
        for line in added:
            print(f"  new:  {line}")
        if not args.check:
            path.write_text("\n".join(found) + "\n", encoding="utf-8")

    if args.check and changed:
        print("run ./scripts/api/sync-route-snapshots.py to update the snapshots")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
