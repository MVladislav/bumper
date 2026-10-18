"""Tests for bumper/web/plugins/api/ecms.py"""

from aiohttp.test_utils import TestClient


async def test_ad_res(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_v2(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v2") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_v3(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v3") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_v3_trailing_slash(webserver_client: TestClient) -> None:
    """Some app screens request the v3 list with a trailing slash."""
    async with webserver_client.get("/api/ecms/app/ad/res/v3/") as resp:
        assert resp.status == 200
        assert (await resp.json())["code"] == 0


async def test_ad_res_unknown_version(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/ad/res/v4") as resp:
        assert resp.status == 404


async def test_user_theme(webserver_client: TestClient) -> None:
    async with webserver_client.get("/api/ecms/app/user/theme") as resp:
        assert resp.status == 200
