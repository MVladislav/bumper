"""The shape of every endpoint.

The snapshot pins the shape of every endpoint, the way `routes.txt` pins the
urls. A change to a shape is a change to what the app reads, so it has to be
a deliberate one: the test fails when a shape changes, and the diff shows
which.

An endpoint that answers a document of its own has no shape and is marked
`raw` - that is the marker for an endpoint that was never given one.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from bumper.web.envelope import describe

SNAPSHOT = Path(__file__).with_name("shapes.txt")


def _routes(router: web.UrlDispatcher) -> Iterator[tuple[str, Any]]:
    """Yield every route of a router, with the handler behind it."""
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


@pytest.mark.usefixtures("clean_database")
async def test_the_shape_of_every_endpoint_matches_the_snapshot(webserver_client: TestClient) -> None:
    """The shape of every endpoint still matches the snapshot."""
    app = webserver_client.server.app
    found = sorted(f"{path} {shape}" for path, handler in _routes(app.router) for shape in [_shape_of(handler)])

    expected = [line.strip() for line in SNAPSHOT.read_text(encoding="utf-8").splitlines() if line.strip()]

    missing = sorted(set(expected) - set(found))
    added = sorted(set(found) - set(expected))

    assert not missing, f"shapes that are gone: {missing}"
    assert not added, f"shapes that are new: {added}"
