"""Tests for the shop endpoints."""

from aiohttp.test_utils import TestClient
import pytest

from tests.web.helpers import get_json

_PRIVATE = "/v1/private/us/en/dev_1234/global_e/3.16.0/google_play/1"


@pytest.mark.usefixtures("clean_database")
async def test_country_config_uses_the_language_of_the_path(webserver_client: TestClient) -> None:
    """The default language follows the language segment, not the country."""
    _status, result = await get_json(webserver_client, f"{_PRIVATE}/osmall/getCountryConfig")
    assert result["data"]["defaultLang"] == "EN"


@pytest.mark.usefixtures("clean_database")
async def test_get_bonus_points_returns_zero_for_requested_products(webserver_client: TestClient) -> None:
    """Products in the local store have no bonus points."""
    _status, result = await get_json(webserver_client, f"{_PRIVATE}/osmall/proxy/product/get-bonus-points?ids=12,34")
    assert result["data"] == {
        "12": {
            "bonus_points": 0.0,
            "distribution_multiple": 0.0,
            "distribution_multiple_up": 0.0,
            "description": "",
        },
        "34": {
            "bonus_points": 0.0,
            "distribution_multiple": 0.0,
            "distribution_multiple_up": 0.0,
            "description": "",
        },
    }


@pytest.mark.usefixtures("clean_database")
async def test_get_product_tags_marks_requested_products_unavailable(webserver_client: TestClient) -> None:
    """The local store has no price activity tags."""
    _status, result = await get_json(
        webserver_client,
        f"{_PRIVATE}/osmall/proxy/go/marketing/common/v1/price-activity/get-product-tag?product_ids=12,34",
    )
    assert result["data"] == {"list": [{"product_id": 12.0, "show_tag": False}, {"product_id": 34.0, "show_tag": False}]}


@pytest.mark.usefixtures("clean_database")
async def test_osmall2_pages_return_empty_content_when_unconfigured(webserver_client: TestClient) -> None:
    """The shop pages load successfully without local catalog content."""
    requests = {
        "getTopBannerList": {"adInfoList": []},
        "getRecommendGoods": {"materialNo": None, "mid": None, "nickName": None, "goodsList": []},
        "geActivityZoneList": {"adInfoList": []},
        "articleList": {"articleList": []},
    }
    for endpoint, expected_data in requests.items():
        status, body = await get_json(webserver_client, f"{_PRIVATE}/osmall2/index/{endpoint}")
        assert status == 200
        assert body["data"] == expected_data


@pytest.mark.usefixtures("clean_database")
async def test_osmall2_layout_filters_by_accepted_module_type(webserver_client: TestClient) -> None:
    """The shop layout contains only modules the app accepts."""
    status, body = await get_json(
        webserver_client,
        f"{_PRIVATE}/osmall2/index/getLayout?acceptedModuleType=TOP_BANNER,RECOMMEND_PRODUCT",
    )
    assert status == 200
    data = body["data"]

    assert data["indexId"] == "20251105163649_63199af1835f121fafb4e21477e52f0b"
    assert data["bgImgUrlNv"] is None
    assert [entry["moduleType"] for entry in data["indexItemList"]] == ["TOP_BANNER", "RECOMMEND_PRODUCT"]


@pytest.mark.usefixtures("clean_database")
async def test_express_icons_are_empty_without_store_data(webserver_client: TestClient) -> None:
    """The shop express icon request succeeds with no configured icons."""
    status, body = await get_json(webserver_client, f"{_PRIVATE}/osmall/proxy/v2/web/express-icon/index")
    assert status == 200
    assert body["data"] == []
