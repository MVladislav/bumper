"""The shape of every API answer.

`tests/web/response_shapes.json` holds the reference shape and
`tests/web/response_shapes_bumper.json` the shape this server produces. Both
hold the keys of an answer and the type of each.

The test checks this server against the reference, so a shape that drifts is
caught here and not by the app.
"""

import json
from pathlib import Path
import re
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from bumper.web.envelope import Template

#: The reference answers.
REFERENCE = Path(__file__).with_name("response_shapes.json")
#: The answers of this server.
BUMPER = Path(__file__).with_name("response_shapes_bumper.json")


def _shapes() -> dict[str, dict[str, list[dict[str, str]]]]:
    """Return the shape of every answer.

    The reference answers come first: they are what the app expects. The
    answers of this server fill in the endpoints the reference does not cover.
    """
    shapes: dict[str, dict[str, list[dict[str, str]]]] = json.loads(BUMPER.read_text(encoding="utf-8"))
    shapes.update(json.loads(REFERENCE.read_text(encoding="utf-8")))
    return shapes


def _routes(app: web.Application) -> list[tuple[str, Any]]:
    """Return every route of the app, with the path it answers."""
    return [(resource.canonical, route.handler) for resource in app.router.resources() for route in resource]


def _matcher(path: str) -> re.Pattern[str]:
    """Return the pattern a path of the traffic matches on."""
    parts = [re.escape(part) for part in path.split("/")]
    pattern = "/".join(part if part.startswith("<") else r"[^/]+" for part in parts)
    return re.compile(f"^{pattern}$")


def _find(routes: list[tuple[str, Any]], path: str) -> Any | None:
    """Return the handler of the route that answers a path."""
    for canonical, handler in routes:
        if canonical == path:
            return handler
    matcher = _matcher(path)
    for canonical, handler in routes:
        if matcher.match(canonical):
            return handler
    return None


def _template_of(handler: Any) -> Template | None:
    """Return the shape a route answers with, if it has one."""
    if (template := getattr(handler, "template", None)) is not None:
        return template
    operations = getattr(handler, "operations", None)
    if operations:
        return next(iter(operations.values())).template
    return None


def _operation_template(handler: Any, operation: str) -> Template | None:
    """Return the shape of one operation of a route."""
    operations = getattr(handler, "operations", None)
    if not operations:
        return None
    if (found := operations.get(operation)) is not None:
        return found.template
    return None


@pytest.mark.usefixtures("clean_database")
async def test_the_answers_have_the_shape_the_traffic_shows(webserver_client: TestClient) -> None:
    """Every answer of the traffic has the shape this server answers with."""
    routes = _routes(webserver_client.server.app)

    checked = 0
    problems: list[str] = []

    for key, expected in _shapes().items():
        path, _, operation = key.partition("#")
        handler = _find(routes, path)
        if handler is None:
            continue

        template = _operation_template(handler, operation) if operation else _template_of(handler)
        if template is None:
            # The route answers with a document of its own, not with a
            # payload in a shape.
            continue

        shapes: list[set[str]] = []
        for answers in expected.values():
            shapes.extend(set(shape) for shape in answers)
        # The keys every answer of the traffic carries, and the keys one of
        # them carries.
        common = set.intersection(*shapes)
        union = set.union(*shapes)

        fixed = template.keys()
        payload = {template.data_key} if template.data_key and not template.flat else set()

        if invented := fixed - union:
            problems.append(f"{key}: the answer carries {sorted(invented)}, which the traffic does not show")
        if not template.flat and (missing := common - fixed - payload):
            # A flat answer puts the payload in the body, so its keys are
            # the keys of the payload and not of the shape.
            problems.append(f"{key}: the answer is missing {sorted(missing)}")
        checked += 1

    assert checked > 20, "the shapes of the traffic were not checked"
    assert not problems, "\n".join(problems)
