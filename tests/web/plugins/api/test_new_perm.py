"""Tests for bumper/web/plugins/api/new_perm.py."""

from aiohttp.test_utils import TestClient
import jwt
import pytest

from tests.web.helpers import post_json


@pytest.mark.usefixtures("clean_database")
async def test_sst_issue_success(webserver_client: TestClient) -> None:
    acl = "read:write"
    exp = 3600
    sub = "user_sub_1"
    status, body = await post_json(
        webserver_client,
        "/api/new-perm/token/sst/issue",
        json={"acl": acl, "exp": exp, "sub": sub},
    )
    assert status == 200
    assert body["code"] == 0
    assert body["msg"] == "success"
    token = body["data"]["data"]["token"]
    assert token.startswith("SST.")
    payload = jwt.decode(token[len("SST.") :], options={"verify_signature": False})
    assert payload["t"] == "SST"
    assert payload["acl"] == acl
    assert payload["sub"] == sub
    assert payload["grant"] == sub
    assert payload["exp"] - payload["iat"] == exp


@pytest.mark.usefixtures("clean_database")
async def test_sst_issue_missing_fields(webserver_client: TestClient) -> None:
    async with webserver_client.post("/api/new-perm/token/sst/issue", json={}) as resp:
        assert resp.status == 400
        text = await resp.text()
    assert text == "Missing required fields: acl, exp, sub"
