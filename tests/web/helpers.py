"""Shared helpers for the web-layer tests.

Centralising the small request/response boilerplate keeps the individual test
modules focused on what they actually assert instead of on aiohttp plumbing.
"""

from typing import Any

from aiohttp.test_utils import TestClient


async def get_json(
    client: TestClient,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    """GET ``path`` and return ``(status, parsed JSON body)``."""
    async with client.get(path, headers=headers) as response:
        body = await response.json()
        return response.status, body


async def post_json(
    client: TestClient,
    path: str,
    *,
    json: Any = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    """POST ``path`` with an optional JSON body and return ``(status, body)``."""
    async with client.post(path, json=json, headers=headers) as response:
        body = await response.json()
        return response.status, body
