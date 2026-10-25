"""The route table of the Ecovacs API.

The snapshot pins the url of every endpoint. A change to it is a change to
what the app can call, so it has to be a deliberate one: the test fails when
a route is added, removed or renamed, and the diff shows which.
"""

from collections.abc import Iterator
from pathlib import Path

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

SNAPSHOT = Path(__file__).with_name("routes.txt")


def _routes(router: web.UrlDispatcher) -> Iterator[str]:
    """Yield every route of a router, including the ones of its sub apps."""
    for resource in router.resources():
        info = resource.get_info()
        if (app := info.get("app")) is not None:
            yield from _routes(app.router)
            continue
        path = resource.canonical
        for route in resource:
            yield f"{route.method} {path}"


@pytest.mark.usefixtures("clean_database")
async def test_route_table_matches_the_snapshot(webserver_client: TestClient) -> None:
    """The urls of the endpoints are what the app calls; they may not drift."""
    app = webserver_client.server.app
    found = sorted(set(_routes(app.router)))

    expected = [line.strip() for line in SNAPSHOT.read_text(encoding="utf-8").splitlines() if line.strip()]

    missing = sorted(set(expected) - set(found))
    added = sorted(set(found) - set(expected))

    assert not missing, f"routes that are gone: {missing}"
    assert not added, f"routes that are new: {added}"
