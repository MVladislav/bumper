"""Tests for bumper/web/payloads.py"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from bumper.web import payloads
from bumper.web.payloads import (
    HOME_ROLE_IDS,
    HOME_ROLE_IDS_NAMED,
    config_faq,
    device_info,
    home_infos,
    member_info,
    role_infos,
    user_info,
)
from bumper.web.utils.models import BumperUser


def _bot(class_id: str = "ls1ok3", **fields: Any) -> MagicMock:
    """Return a bot with the fields the builder reads."""
    bot = MagicMock()
    bot.class_id = class_id
    bot.mqtt_connection = True
    bot.xmpp_connection = False
    bot.userid = "user1"
    bot.as_dict.return_value = {
        "class": class_id,
        "company": "eco-ng",
        "did": "did1",
        "name": "robot",
        "nick": "robot",
        "resource": "res1",
        "mqtt_connection": True,
        "xmpp_connection": False,
    }
    for key, value in fields.items():
        setattr(bot, key, value)
    return bot


def _product_iot(smart_type: str | None = None) -> list[dict[str, Any]]:
    """Return a product map with one robot."""
    product: dict[str, Any] = {
        "_id": "pid1",
        "materialNo": "mat1",
        "name": "DEEBOT X",
        "model": "m1",
        "UILogicId": "ui1",
        "ota": {},
        "iconUrl": "icon1",
    }
    if smart_type is not None:
        product["smartType"] = smart_type
    return [{"classid": "ls1ok3", "product": product}]


def test_the_roles_are_named_once() -> None:
    """The roles of a home are the data of the domain."""
    assert len(HOME_ROLE_IDS) == 10
    assert len(HOME_ROLE_IDS_NAMED) == 10
    assert tuple(role_id for role_id, _ in HOME_ROLE_IDS_NAMED) == HOME_ROLE_IDS


def test_the_role_infos_carry_the_id_and_the_name() -> None:
    roles = role_infos()

    assert len(roles) == 10
    assert roles[0] == {"id": HOME_ROLE_IDS[0], "name": "Fraternal grandpa", "isUse": False}


def test_the_home_infos_are_numbered() -> None:
    user = BumperUser(userid="user1")
    user.username = "bumper"
    user.homeids = ["home1", "home2"]

    homes = home_infos(user)

    assert [home["name"] for home in homes] == ["My Home (0)", "My Home (1)"]
    assert homes[0]["homeId"] == "home1"
    assert homes[0]["createUser"] == "user1"
    assert homes[0]["createUserName"] == "bumper"
    assert homes[0]["type"] == "own"


def test_the_member_info_carries_the_role() -> None:
    user = BumperUser(userid="user1")
    user.nickname = "smart-eco"

    member = member_info(user, HOME_ROLE_IDS[0], "Fraternal grandpa")

    assert member["roleId"] == HOME_ROLE_IDS[0]
    assert member["roleName"] == "Fraternal grandpa"
    assert member["uid"] == "user1"
    assert member["id"] == "user1"
    assert member["isAdmin"] == 2
    assert member["status"] == 1


def test_the_user_info_carries_the_mail_of_the_settings() -> None:
    user = BumperUser(userid="user1")
    user.nickname = "smart-eco"

    info = user_info(user)

    assert info["uid"] == "user1"
    assert info["nick"] == "smart-eco"
    assert info["isAdmin"] is True
    assert info["mail"]


def test_the_config_faq_points_at_the_service_of_the_files() -> None:
    faq = config_faq()

    assert set(faq) == {"wifiFAQUrl", "notFoundAPUrl", "configFailedUrl"}
    for url in faq.values():
        assert url.startswith("https://")
        assert "/api/pim/" in url


def test_a_device_that_is_not_in_the_product_map_is_not_part_of_the_account() -> None:
    payloads.get_product_iot_map = list  # type: ignore[assignment]

    assert device_info(_bot()) is None


def test_the_device_info_carries_the_product() -> None:
    product_iot = _product_iot()
    payloads.get_product_iot_map = lambda: product_iot  # type: ignore[assignment]

    result = device_info(_bot())

    assert result is not None
    assert result["pid"] == "pid1"
    assert result["materialNo"] == "mat1"
    assert result["deviceName"] == "DEEBOT X"
    assert result["model"] == "m1"
    assert result["icon"] == "icon1"
    assert result["product_category"] == "DEEBOT"
    assert result["status"] == 1
    assert result["shareable"] is True
    assert result["sharedDevice"] is False
    assert result["offmap"] is True
    assert result["service"]["jmq"].startswith("jmq-ngiot-eu.")
    assert result["service"]["mqs"].startswith("api-ngiot.")


@pytest.mark.parametrize(
    ("smart_type", "tmallstand", "bt_mode"),
    [
        ("MQ_AP", True, None),
        ("BLAP", None, True),
        (None, False, None),
    ],
)
def test_the_scode_follows_the_kind_of_the_robot(
    smart_type: str | None,
    tmallstand: bool | None,
    bt_mode: bool | None,
) -> None:
    """The capabilities of the robot decide the flags of the answer."""
    payloads.get_product_iot_map = lambda: _product_iot(smart_type)

    result = device_info(_bot())

    assert result is not None
    scode = result["scode"]
    assert scode["battery"] is True
    assert scode.get("tmallstand") is tmallstand
    assert scode.get("bt_mode") is bt_mode


def test_the_layout_of_the_shop_is_the_same_on_every_page() -> None:
    """The pages of the shop differ in their modules, not in their shape."""
    layout = payloads.shop_layout(["TOP_BANNER", "CATEGORY"])

    assert set(layout) == {
        "bgColorNo",
        "bgImgUrlBenefit",
        "bgImgUrlNv",
        "indexId",
        "indexItemList",
    }
    assert layout["indexItemList"] == [{"moduleType": "TOP_BANNER"}, {"moduleType": "CATEGORY"}]


def test_the_banners_of_the_shop_carry_their_goods_and_their_advertisement() -> None:
    """A banner is a goods or an advertisement."""
    banners = payloads.shop_banner_list()["bannerInfoList"]

    assert len(banners) == 3
    assert banners[0]["bannerType"] == "GOODS"
    assert banners[0]["goodsInfo"] is not None
    assert banners[0]["adInfo"] is None
    assert banners[1]["bannerType"] == "AD"
    assert banners[1]["adInfo"] is not None
    assert banners[1]["goodsInfo"] is None


def test_the_categories_of_the_shop_are_the_robots_and_the_accessories() -> None:
    """The categories of the goods of the shop."""
    categories = payloads.shop_category_list()["categoryList"]

    assert [category["categoryId"] for category in categories] == [
        "deebot",
        "winbot",
        "atmobot",
        "accessory",
        "goat",
    ]


def test_the_help_carries_the_products_and_the_questions() -> None:
    """The index of the help and the help of a product."""
    index = payloads.help_index()

    assert len(index["indexProductList"]) == 8
    assert index["moreHelpModuleList"] == []
    for product in index["indexProductList"]:
        assert product["imgUrl"].startswith("https://")
        assert product["productId"]

    product = payloads.help_product_index()

    assert set(product) == {
        "faqResponse",
        "headImgResponse",
        "instructions",
        "productResponse",
        "skillsResponse",
        "videoList",
    }
    assert len(product["faqResponse"]["faqList"]) == 8
    assert product["faqResponse"]["hasMore"] == "Y"
    assert len(product["videoList"]) == 8
