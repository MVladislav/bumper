"""Tests for bumper/web/plugins/api/pim/consumable.py"""

from aiohttp.test_utils import TestClient
import pytest

from bumper.web.hosts import pim_host
from tests.web.helpers import get_json, post_json

_CONSUMABLE_TYPES = ["sideBrush", "brush", "heap", "dustBag", "oneTimeCloth", "unitCare", "dModule"]


@pytest.mark.usefixtures("clean_database")
async def test_get_purchase_url_lists_every_consumable(webserver_client: TestClient) -> None:
    """The purchase endpoint answers with one entry per consumable type."""
    status, body = await get_json(webserver_client, "/api/pim/consumable/getPurchaseUrl")
    assert status == 200
    assert body["code"] == 0
    assert body["msg"] == "success"
    entries = body["data"]
    assert [entry["type"] for entry in entries] == _CONSUMABLE_TYPES
    for entry in entries:
        assert entry["icon"].startswith(f"https://{pim_host()}/api/pim/file/get/")
        assert entry["url"] == ""
        assert entry["paramType"] == "URL"
        assert entry["hasLifeSpan"] == 0
        assert entry["desc"]["images"]
        assert entry["desc"]["content"]


@pytest.mark.usefixtures("clean_database")
async def test_get_purchase_url_is_served_for_post_too(webserver_client: TestClient) -> None:
    """The view answers with the same list for any method."""
    status, body = await post_json(webserver_client, "/api/pim/consumable/getPurchaseUrl")
    assert status == 200
    assert body["code"] == 0
    assert [entry["type"] for entry in body["data"]] == _CONSUMABLE_TYPES
