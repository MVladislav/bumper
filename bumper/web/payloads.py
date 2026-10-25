"""The payloads of the API.

The app reads the answers into models of its own, so the fields are named
here once, with the type they have. A builder puts them together, and a
test can call a builder without a server.
"""

import copy
import hashlib
from typing import Any, NotRequired, TypedDict

from bumper.db import bot_repo
from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc
from bumper.web.hosts import api_host, codepush_host, pim_host, xmpp_host
from bumper.web.static_api import (
    get_codepush_update_check,
    get_codepush_update_check_mapping,
    get_config_groups_robot,
    get_product_category,
    get_product_iot_map,
)
from bumper.web.utils.models import BumperUser, VacBotDevice


class DeviceService(TypedDict):
    """The hosts of a device."""

    jmq: str
    mqs: str


class DeviceInfo(TypedDict):
    """A device of the account."""

    UILogicId: NotRequired[str]
    appLogicId: NotRequired[str]
    bindTs: int
    btMac: NotRequired[str]
    btName: NotRequired[str]
    cfg: NotRequired[str]
    deviceName: NotRequired[str]
    did: str
    icon: NotRequired[str]
    index: NotRequired[int]
    mac: NotRequired[str]
    materialNo: NotRequired[str]
    mid: NotRequired[str]
    model: NotRequired[str]
    name: str
    nickName: NotRequired[str]
    nickname: NotRequired[str]
    offmap: bool
    ota: NotRequired[bool]
    otaUpgrade: dict[str, Any]
    pid: NotRequired[str]
    product_category: NotRequired[str]
    resource: str
    scode: dict[str, bool]
    service: DeviceService
    shareable: bool
    sharedDevice: bool
    status: int
    updateInfo: dict[str, Any]


class HomeInfo(TypedDict):
    """A home of the account."""

    createTime: int
    createUser: str
    createUserName: str
    firstCreate: bool
    homeId: str
    name: str
    type: str


class MemberInfo(TypedDict):
    """A member of a home."""

    createTime: int
    id: str
    isAdmin: int
    name: str
    roleId: str
    roleName: str
    status: int
    uid: str


class RoleInfo(TypedDict):
    """A role of a home."""

    id: str
    isUse: bool
    name: str


class UserInfo(TypedDict):
    """A user of the account."""

    avatar: str
    isAdmin: bool
    mail: str
    mobile: str
    nick: str
    uid: str


#: The roles of a home, with the id of each.
HOME_ROLE_IDS_NAMED: tuple[tuple[str, str], ...] = (
    ("62613c516d224ab8b32468fb", "Fraternal grandpa"),  # pragma: allowlist secret
    ("62613c516d224ab8b32468fc", "Fraternal grandma"),  # pragma: allowlist secret
    ("62613c516d224ab8b32468fd", "Dad"),  # pragma: allowlist secret
    ("62613c516d224ab8b32468fe", "Mom"),  # pragma: allowlist secret
    ("62613c516d224ab8b32468ff", "Older brother"),  # pragma: allowlist secret
    ("62613c516d224ab8b3246900", "Younger brother"),  # pragma: allowlist secret
    ("62613c516d224ab8b3246901", "Older sister"),  # pragma: allowlist secret
    ("62613c516d224ab8b3246902", "Younger sister"),  # pragma: allowlist secret
    ("62613c516d224ab8b3246903", "Husband"),  # pragma: allowlist secret
    ("62613c516d224ab8b3246904", "Wife"),  # pragma: allowlist secret
)

#: The ids of the roles of a home.
HOME_ROLE_IDS: tuple[str, ...] = tuple(role_id for role_id, _ in HOME_ROLE_IDS_NAMED)


def device_list(user: BumperUser | None) -> list[DeviceInfo]:
    """Return the devices of the account.

    Robots are shared with every local account because Bumper has no account
    invitation or robot-sharing flow. A robot not registered with Bumper is
    not part of any answer.
    """
    if user is None:
        return []
    owned = set(user.bots)
    return [
        device
        for bot in bot_repo.list_all()
        if bot.did in owned and bot.class_id and bot.class_id != "" and (device := device_info(bot)) is not None
    ]


def device_info(bot: VacBotDevice) -> DeviceInfo | None:
    """Return the entry of a device, with the product it belongs to.

    A device that is not in the product map is not part of the account.
    """
    for botprod in get_product_iot_map():
        if botprod["classid"] != bot.class_id:
            continue

        result: dict[str, Any] = copy.deepcopy(bot.as_dict())
        result.pop("mqtt_connection")
        result.pop("xmpp_connection")

        robot = get_config_groups_robot(result.get("class"))

        if (botprod_invent := botprod.get("product")) is not None:
            result["pid"] = botprod_invent["_id"]
            result["materialNo"] = botprod_invent["materialNo"]
            result["deviceName"] = botprod_invent["name"]
            result["model"] = botprod_invent["model"]
            result["UILogicId"] = botprod_invent["UILogicId"]
            result["ota"] = botprod_invent["ota"]
            result["icon"] = botprod_invent["iconUrl"]

            if not robot:
                # some class-id's are not located inside 'configGroupsResponse', fallback to 'groupName'
                robot = get_config_groups_robot(value=result.get("deviceName"), key="groupName")
            result["product_category"] = get_product_category(botprod_invent["name"], robot)

            result["scode"] = {"battery": True}
            smart_type: str | None = botprod_invent.get("smartType")
            if smart_type and smart_type.startswith("MQ"):  # MQ_AP|MQ_APM
                result["scode"].update(
                    {
                        "tmallstand": True,
                        "video": True,
                        "clean": True,
                        "charge": True,
                        "chargestate": True,
                    },
                )
            elif smart_type and smart_type.startswith("BLAP"):  # BLAP|BLAP2|BLAPG
                result["scode"].update(
                    {
                        "appArchVer": "2.0",
                        "bt_mode": True,
                        "ff_mode": True,
                        "fwPlat": "DZ",
                    },
                )
                result["btName"] = ""
                result["btMac"] = ""
            else:  # BT|HK_AP|QRP|SPA
                result["scode"].update(
                    {
                        "tmallstand": False,
                        "video": False,
                        "clean": True,
                        "charge": True,
                        "chargestate": True,
                    },
                )

        result["status"] = 1 if bot.mqtt_connection or bot.xmpp_connection else 0

        result["otaUpgrade"] = {}
        result["updateInfo"] = {"changeLog": "", "needUpdate": False}
        result["shareable"] = bool(bot.mqtt_connection)
        result["sharedDevice"] = False

        result["homeId"] = bumper_isc.DEFAULT_HOME_ID
        result["homeSort"] = 1

        result["bindTs"] = utils.get_current_time_as_millis()
        result["offmap"] = True

        result["service"] = {
            "jmq": api_host("jmq-ngiot-eu", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_2),
            "mqs": api_host("api-ngiot", bumper_isc.DOMAIN_MAIN, bumper_isc.DOM_SUB_1),
        }

        return result  # type: ignore[return-value]
    return None


def home_infos(user: BumperUser) -> list[HomeInfo]:
    """Return the homes of a user."""
    return [
        {
            "createTime": utils.get_current_time_as_millis(),
            "createUser": user.iot_id,
            "createUserName": user.username,
            "firstCreate": False,
            "homeId": home_id,
            "name": f"My Home ({index})",
            "type": "own",
        }
        for index, home_id in enumerate(user.homeids)
    ]


def member_info(user: BumperUser, role_id: str, role_name: str) -> MemberInfo:
    """Return a member of a home."""
    return {
        "createTime": utils.get_current_time_as_millis(),
        "id": user.iot_id,
        "isAdmin": 2,
        "name": user.nickname,
        "roleId": role_id,
        "roleName": role_name,
        "status": 1,
        "uid": user.iot_id,
    }


def role_infos() -> list[RoleInfo]:
    """Return the roles of a home."""
    return [{"id": role_id, "name": name, "isUse": False} for role_id, name in HOME_ROLE_IDS_NAMED]


def member_no(user_name: str) -> str:
    """Return the number of the member.

    The API numbers its members; Bumper makes a number of its own, the same
    for the same user.
    """
    digest = hashlib.sha256(user_name.encode()).hexdigest()
    return str(int(digest[:12], 16) % 10**12).zfill(12)


def user_info(user: BumperUser) -> UserInfo:
    """Return a user of the account."""
    return {
        "avatar": "",
        "isAdmin": True,
        "mail": user.email or bumper_isc.USER_MAIL_DEFAULT,
        "mobile": "",
        "nick": user.nickname,
        "uid": user.iot_id,
    }


def codepush_update_check(
    deployment_key: str,
    label: str,
    package_hash: str,
    package_name: str | None,
    app_version: str,
    deployment_name: str,
) -> dict[str, Any]:
    """Return the answer of the CodePush update check.

    The document of a deployment that is not known says that there is no
    update, with the version of the app as the range it applies to.
    """
    if deployment_key == "" and package_name:
        deployment_key = get_codepush_update_check_mapping().get(package_name, "")

    response: dict[str, Any] = get_codepush_update_check().get(
        deployment_key,
        {
            "update_info": {
                "download_url": "",
                "description": "",
                "is_available": False,
                "is_disabled": True,
                "target_binary_range": app_version,
                "label": label,
                "package_hash": package_hash,
                "package_size": 0,
                "should_run_binary_version": False,
                "update_app_version": False,
                "is_mandatory": False,
                "deployment_key": deployment_key,
                "deployment_name": deployment_name,
                "publish_time": 0,
            },
        },
    )
    return _codepush_download_url(response)


def _codepush_download_url(response: dict[str, Any]) -> dict[str, Any]:
    """Point the download url at Bumper, if the packages are served here.

    The app downloads the package from the url of the answer, so the url has
    to name the host that answers for Bumper.
    """
    if not bumper_isc.CODEPUSH_LOCAL_PACKAGE:
        return response

    update_info = response.get("update_info")
    if not isinstance(update_info, dict):
        return response

    deployment_key = str(update_info.get("deployment_key", ""))
    if not deployment_key or not update_info.get("download_url"):
        return response

    return {
        **response,
        "update_info": {
            **update_info,
            "download_url": codepush_download_url(deployment_key),
        },
    }


def codepush_download_url(deployment_key: str) -> str:
    """Return the url the app downloads the CodePush package from."""
    return f"https://{codepush_host()}/api/appsvr/codepush/download/{deployment_key}"


def config_faq() -> dict[str, str]:
    """Return the links of the pages that answer the questions of the setup."""
    host = pim_host()
    return {
        "wifiFAQUrl": f"https://{host}/api/pim/faqproblem.html?lang=en&defaultLang=en",
        "notFoundAPUrl": f"https://{host}/api/pim/findDbWifi.html?lang=en&defaultLang=en",
        "configFailedUrl": f"https://{host}/api/pim/configfail.html?lang=en&defaultLang=en",
    }


class AgreementEntry(TypedDict):
    """An agreement the user accepts."""

    acceptTime: int | None
    force: str | None
    id: str
    type: str
    updateDesc: str | None
    url: str | None
    version: str


class AgreementInfo(TypedDict):
    """The agreements of a user."""

    acceptList: list[AgreementEntry]
    newestList: list[AgreementEntry]


class IntegralCommon(TypedDict):
    """The points and the level every member has."""

    availableGeneralIntegral: int
    availableLimitedIntegral: int
    benefitList: list[Any]
    expiringPointDesc: str | None
    expiringPointExplain: str | None
    expiringPoints: int | None
    frozenIntegral: int
    goodsDetailIntegralDesc: str
    integral: int
    integralDescWapUrl: str
    isCountryOpen: str
    isLimitedIntegralOpen: str
    isMember: str
    levelName: str
    remainingDay: int | None


class MemberIntegral(IntegralCommon):
    """The points of a member of the store."""

    expiringLimitedPointExplain: str | None
    expiringLimitedPointShowDesc: str | None
    expiringLimitedPoints: int | None
    frozenIntegralDesc: str
    level: int
    levelIconUrl: str
    memberDescWapUrl: str
    shoppingGetIntegralShowDesc: str | None
    shoppingGetIntegraltimes: int | None
    shoppingGetIntegraltimesShowDesc: str | None
    shoppingGetIntegraltimesUp: int | None
    shoppingGetIntegraltimesUpShowDesc: str | None


class AccountIntegral(IntegralCommon):
    """The points that are shown with the account of a user."""

    frozenIntegralTips: str
    intlMemberMallUrl: str
    vipLevelIconUrl: str


class UserAccountInfo(TypedDict):
    """The account of a user."""

    email: str
    hasMobile: str
    hasPassword: str
    headIco: str
    intlMemberInfo: AccountIntegral
    loginName: str
    mobile: str | None
    mobileAreaNo: str | None
    nickname: str
    obfuscatedMobile: str | None
    thirdLoginInfoList: list[dict[str, str]]
    uid: str
    userName: str
    userShowName: str


class ServiceList(TypedDict):
    """The services the app talks to."""

    account: str
    adv: str
    dc: str
    jmq: str
    lb: str
    magw: str
    msgcloud: str
    ngiot: str
    ngiotLb: str
    nlp: str
    rop: str
    bigdata: str
    base: str
    eis: str
    codepush: str
    setApConfig: dict[str, str]


class DeviceProp(TypedDict):
    """One property of a device."""

    key: str
    value: str
    ts: str


class DeviceProps(TypedDict):
    """The properties of a device."""

    did: str | None
    ts: int
    props: list[DeviceProp]


def agreement_entry(
    agreement_id: str,
    agreement_type: str,
    version: str,
    accept_time: int | None = None,
    force: str | None = None,
    update_desc: str | None = None,
    domain: str = "",
) -> AgreementEntry:
    """Return one agreement of a user."""
    url = f"{domain}?id={agreement_id}&language=EN" if domain else None
    return {
        "acceptTime": accept_time,
        "force": force,
        "id": agreement_id,
        "type": agreement_type,
        "updateDesc": update_desc,
        "url": url,
        "version": version,
    }


def member_integral() -> MemberIntegral:
    """Return the points of a member of the store."""
    return {
        "availableGeneralIntegral": 9999,
        "availableLimitedIntegral": 0,
        "benefitList": [],
        "expiringLimitedPointExplain": None,
        "expiringLimitedPointShowDesc": None,
        "expiringLimitedPoints": None,
        "expiringPointDesc": None,
        "expiringPointExplain": None,
        "expiringPoints": None,
        "frozenIntegral": 0,
        "frozenIntegralDesc": "The points will be credited to your member account 20 days after the payment of the order.",
        "goodsDetailIntegralDesc": "Redeem points for discounts!",
        "integral": 9999,
        "integralDescWapUrl": f"https://{bumper_isc.DOMAIN_SEC3}/web/page?no=jusapxaw",
        "isCountryOpen": "Y",
        "isLimitedIntegralOpen": "N",
        "isMember": "Y",
        "level": 1,
        "levelIconUrl": f"https://{bumper_isc.DOMAIN_SEC2}/public/221027/f187b4b72f434fcc9eae655dbb389ac7.png",
        "levelName": "VIP1",
        "memberDescWapUrl": f"https://{bumper_isc.DOMAIN_SEC4}/DE/EN/content/description",
        "remainingDay": None,
        "shoppingGetIntegralShowDesc": None,
        "shoppingGetIntegraltimes": None,
        "shoppingGetIntegraltimesShowDesc": None,
        "shoppingGetIntegraltimesUp": None,
        "shoppingGetIntegraltimesUpShowDesc": None,
    }


def account_integral() -> AccountIntegral:
    """Return the points that are shown with the account of a user."""
    return {
        "availableGeneralIntegral": 0,
        "availableLimitedIntegral": 0,
        "benefitList": [],
        "expiringPointDesc": None,
        "expiringPointExplain": None,
        "expiringPoints": None,
        "frozenIntegral": 0,
        "frozenIntegralTips": "Points will be issued 20 days after order payment. Please wait.",
        "goodsDetailIntegralDesc": "Points will be issued 20 days after order payment. Please wait.",
        "integral": 0,
        "integralDescWapUrl": f"https://{bumper_isc.DOMAIN_SEC3}/web/page?no=hh3yxg4g",
        "intlMemberMallUrl": f"https://{bumper_isc.DOMAIN_SEC1}/us",
        "isCountryOpen": "Y",
        "isLimitedIntegralOpen": "N",
        "isMember": "Y",
        "levelName": "VIP1",
        "remainingDay": None,
        "vipLevelIconUrl": f"https://{bumper_isc.DOMAIN_SEC2}/public/220628/d01e939518354ee0af5c88a5269e27d8.png",
    }


def user_account_info(user: BumperUser) -> UserAccountInfo:
    """Return the account of a user."""
    return {
        "email": user.email or bumper_isc.USER_MAIL_DEFAULT,
        "hasMobile": "N",
        "hasPassword": "Y",
        "headIco": "",
        "intlMemberInfo": account_integral(),
        "loginName": user.login_name or user.username,
        "mobile": None,
        "mobileAreaNo": None,
        "nickname": user.nickname,
        "obfuscatedMobile": None,
        "thirdLoginInfoList": [{"accountType": "WeChat", "hasBind": "N"}],
        "uid": user.account_id,
        "userName": user.username,
        "userShowName": user.username,
    }


def service_list(area_code: str) -> ServiceList:
    """Return the services the app talks to."""
    domain = bumper_isc.DOMAIN_MAIN
    region = bumper_isc.DOM_SUB_1
    return {
        "account": api_host("users-base", domain, region),
        "adv": api_host("adv-app", domain, region),
        "dc": utils.get_dc_code(area_code),
        "jmq": api_host("jmq-ngiot-eu", domain, bumper_isc.DOM_SUB_2),
        "lb": api_host("lbo", domain, region),
        "magw": api_host("api-app", domain, region),
        "msgcloud": xmpp_host("msg-eu", domain),
        "ngiot": api_host("api-ngiot", domain, region),
        "ngiotLb": api_host("jmq-ngiot-de", domain, bumper_isc.DOM_SUB_3),
        "nlp": api_host("iot-api-nlp", domain, region),
        "rop": api_host("api-rop", domain, region),
        "bigdata": api_host("bigdata-europe", bumper_isc.DOMAIN_SEC),
        "base": api_host("api-base", domain, region),
        "eis": api_host("eis-nlp", domain, region),
        "codepush": api_host("codepush-base", domain, region),
        "setApConfig": {
            "a": area_code,
            "r": domain,
            "v": "ww",
        },
    }


class ShopLayout(TypedDict):
    """The layout of a page of the shop."""

    bgColorNo: str
    bgImgUrlBenefit: str
    bgImgUrlNv: str
    indexId: str
    indexItemList: list[dict[str, str]]


class ShopGoodsInfo(TypedDict):
    """The goods of a banner of the shop."""

    buyFlag: str
    goodsId: str
    goodsSubTitle: str | None
    goodsTitle: str | None
    goodsType: str
    imgUrl: str
    mediaType: str | None
    mediaUrl: str | None


class ShopAdInfo(TypedDict):
    """The advertisement of a banner of the shop."""

    adId: str
    adName: str
    clickAction: int
    clickUri: str
    imgUrl: str
    mediaType: str | None
    mediaUrl: str | None
    paramsJson: str | None


class ShopBanner(TypedDict):
    """A banner of the shop."""

    adInfo: ShopAdInfo | None
    bannerType: str
    goodsInfo: ShopGoodsInfo | None


class ShopBannerList(TypedDict):
    """The banners of the shop."""

    bannerInfoList: list[ShopBanner]


class ShopCategory(TypedDict):
    """A category of the goods of the shop."""

    categoryId: str
    categoryImgUrl: str
    categoryName: str
    categoryPageTopImgUrl: str
    categorySubTitle: str


class ShopCategoryList(TypedDict):
    """The categories of the goods of the shop."""

    categoryList: list[ShopCategory]


class ShopGoodsList(TypedDict):
    """The goods the shop recommends."""

    goodsList: list[dict[str, Any]]
    materialNo: str | None
    mid: str | None
    nickName: str | None


class DiscoverLabel(TypedDict):
    """A label of the discover screen."""

    labelId: str
    labelName: str


def discover_labels() -> list[DiscoverLabel]:
    """Return the labels the discover screen filters the articles with."""
    return [
        {"labelId": "20240326074945_754182033ca9b46b2036f79f6f29bb45", "labelName": "New Launch"},
        {"labelId": "20240326083523_6e6a3e599ac23bfbbe75d80dcef45b8d", "labelName": "Unboxing & Review"},
        {"labelId": "20240411032201_ea3feb69afc5acd7a83f793feb008719", "labelName": "RoboTech"},
        {"labelId": "20240411033111_8fbd128cf6c467990ec8358d5740a452", "labelName": "Promos & Deals"},
        {"labelId": "20240411034052_4c2c0bef759db354072d59cfe6f2d196", "labelName": "Instructions & Tips"},
    ]


class HelpProduct(TypedDict):
    """A product in the index of the help."""

    imgUrl: str
    isConfNet: str
    marketName: str
    materialNo: str
    model: str
    productId: str


class HelpIndex(TypedDict):
    """The index of the help."""

    indexProductList: list[HelpProduct]
    moreHelpModuleList: list[dict[str, Any]]


class HelpFaq(TypedDict):
    """A question of the help."""

    faqId: str
    title: str
    url: str


class HelpFaqList(TypedDict):
    """The questions of the help of a product."""

    faqList: list[HelpFaq]


class HelpFaqResponse(TypedDict):
    """The questions of the help of a product, with the flag of the rest."""

    faqList: list[HelpFaq]
    hasMore: str


class HelpHeadImg(TypedDict):
    """The image at the top of the help of a product."""

    clickAction: str
    clickURL: str | None
    headImgUrl: str | None
    params: dict[str, Any]


class HelpInstructions(TypedDict):
    """The instructions of a product."""

    downloadUrl: str
    viewUrl: str


class HelpProductInfo(TypedDict):
    """The product the help belongs to."""

    imgUrl: str
    marketName: str
    materialNo: str
    model: str
    productId: str


class HelpVideo(TypedDict):
    """A video of the help of a product."""

    coverImgUrl: str
    url: str
    videoId: str


class HelpProductIndex(TypedDict):
    """The help of a product."""

    faqResponse: HelpFaqResponse
    headImgResponse: HelpHeadImg
    instructions: HelpInstructions
    productResponse: HelpProductInfo
    skillsResponse: None
    videoList: list[HelpVideo]


def shop_layout(index_item_list: list[str]) -> ShopLayout:
    """Return the layout of a page of the shop.

    The modules of the page differ per shop, the shape of the layout does
    not.
    """
    return {
        "bgColorNo": "",
        "bgImgUrlBenefit": "",
        "bgImgUrlNv": "",
        "indexId": "20220929111910_9f988dd276fec8ecaedb5f83bbe227fb",
        "indexItemList": [{"moduleType": module} for module in index_item_list],
    }


def shop_banner_list() -> ShopBannerList:
    """Return the banners of the shop."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return {
        "bannerInfoList": [
            {
                "adInfo": None,
                "bannerType": "GOODS",
                "goodsInfo": {
                    "buyFlag": "N",
                    "goodsId": "243",
                    "goodsSubTitle": None,
                    "goodsTitle": None,
                    "goodsType": "main_goods",
                    "imgUrl": f"{domain}/2023/10/12/20231012043300_c9c28f83f20fcbdd473042e2fe1aae80.jpg",
                    "mediaType": None,
                    "mediaUrl": None,
                },
            },
            {
                "adInfo": {
                    "adId": "20231008031415_3d397f051ae2db32230d1c015d04020c",
                    "adName": "DE-X2 OMNI-white",
                    "clickAction": 3,
                    "clickUri": "GlobalMainProductDetail",
                    "imgUrl": f"{domain}/2023/10/08/20231008031258_11ed602251f180f6501dfdcbba0ab1ad.jpg",
                    "mediaType": None,
                    "mediaUrl": None,
                    "paramsJson": '{"goodsId":"271"}',
                },
                "bannerType": "AD",
                "goodsInfo": None,
            },
            {
                "adInfo": {
                    "adId": "20220929111324_2cdf4a4c07e692b09369a207aab224b8",
                    "adName": "DE-耗材 日常banner",
                    "clickAction": 3,
                    "clickUri": "GlobalAccessoryList",
                    "imgUrl": f"{domain}/2023/08/02/20230802070513_b8db717e7bc8d5e0583bb28a0ea37c23.jpg",
                    "mediaType": None,
                    "mediaUrl": None,
                    "paramsJson": None,
                },
                "bannerType": "AD",
                "goodsInfo": None,
            },
        ],
    }


def shop_category_list() -> ShopCategoryList:
    """Return the categories of the goods of the shop."""
    domain = f"https://{bumper_isc.DOMAIN_SEC2}/upload/global"
    return {
        "categoryList": [
            {
                "categoryId": "deebot",
                "categoryImgUrl": f"{domain}/2022/09/29/20220929102735_3f3c7c2e901a331e0b67ca492fdc3c6a.png",
                "categoryName": "DEEBOT",
                "categoryPageTopImgUrl": f"{domain}/2022/09/29/20220929102846_1049b38781c4873ddce718ba7e5c18b8.jpg",
                "categorySubTitle": "Tomorrow's robots today",
            },
            {
                "categoryId": "winbot",
                "categoryImgUrl": f"{domain}/2022/09/29/20220929102922_3034e697186933d61dfef1cbd9c23795.png",
                "categoryName": "WINBOT",
                "categoryPageTopImgUrl": f"{domain}/2022/09/29/20220929102913_7b64ef5036d146b9c7425f52eb6e31fa.jpg",
                "categorySubTitle": "Spotless windows, so simple, so clean",
            },
            {
                "categoryId": "atmobot",
                "categoryImgUrl": f"{domain}/2022/10/22/20221022141810_84db4431bf3a5d23e2046f6c7e8d4c16.png",
                "categoryName": "AIRBOT",
                "categoryPageTopImgUrl": f"{domain}/2022/10/22/20221022142252_3db74870acc2a1f16052714ba00cdd2b.jpg",
                "categorySubTitle": "A BREAKTHROUGH IN AIR CLEANING",
            },
            {
                "categoryId": "accessory",
                "categoryImgUrl": f"{domain}/2022/09/29/20220929103036_2e6c9f31a0df1d2e286492fdc1ca4253.png",
                "categoryName": "ACCESSORIES",
                "categoryPageTopImgUrl": f"{domain}/2022/12/13/20221213024206_bdbe94f753316a1e779f0d36800b8ab2.jpg",
                "categorySubTitle": "Find the right accessories for your DEEBOT",
            },
            {
                "categoryId": "goat",
                "categoryImgUrl": f"{domain}/2023/03/29/20230329125208_fad7fc1e678b4f55a7520b6e52ad96ee.png",
                "categoryName": "GOAT",
                "categoryPageTopImgUrl": f"{domain}/2023/03/29/20230329125218_bc88e13645ee1538bade4f7618719e35.jpg",
                "categorySubTitle": "A CLASS OF ITS OWN",
            },
        ],
    }


def shop_recommend_goods() -> ShopGoodsList:
    """Return the goods the shop recommends."""
    return {"goodsList": [], "materialNo": None, "mid": None, "nickName": None}


def help_index() -> HelpIndex:
    """Return the index of the help."""
    return {
        "indexProductList": [
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/5cf711aeb0acfc000179ff8a",
                "isConfNet": "Y",
                "marketName": "DEEBOT OZMO/PRO 930 Series",
                "materialNo": "110-1602-0101",
                "model": "DR930",
                "productId": "20200115064102_59428181dfdcae88ea5b745415e30d37",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/606278df4a84d700082b39f1",
                "isConfNet": "Y",
                "marketName": "DEEBOT OZMO 950 Series",
                "materialNo": "110-1820-0101",
                "model": "DX9G",
                "productId": "20200115064101_c871daa7c1cb74f447d4fcdb38040eaf",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/61f0ba7970c881c6bf65ec3d",
                "isConfNet": "Y",
                "marketName": "DEEBOT T10 PLUS",
                "materialNo": "110-2113-0301",
                "model": "CURIE_AES_INT_OK",
                "productId": "20220127010107_783c591a6632cc89c914cc0d8f2d338e",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/624d4e73031bdd7c7b531af9",
                "isConfNet": "N",
                "marketName": "AIRBOT Z1",
                "materialNo": "113-2109-0200",
                "model": "BRUCE_INT",
                "productId": "20220407010045_bd1a7f60c8befe4c79c4e8b8e6f35c76",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/5c874326280fda0001770d2a",
                "isConfNet": "N",
                "marketName": "DEEBOT 500",
                "materialNo": "702-0000-0163",
                "model": "D500",
                "productId": "20200115064057_5aa61e982672ae0c5a1883e3260eb869",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/5c931fef280fda0001770d7e",
                "isConfNet": "N",
                "marketName": "DEEBOT 501",
                "materialNo": "702-0000-0169",
                "model": "D501",
                "productId": "20200115064057_db0462273510a60eaaae32a78923491f",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/5c93204b63023c0001e7faa7",
                "isConfNet": "N",
                "marketName": "DEEBOT 502",
                "materialNo": "702-0000-0161",
                "model": "D502",
                "productId": "20200115064057_7a8ea52adf4b96a8b9752315ae86c8b5",
            },
            {
                "imgUrl": f"https://{pim_host()}/api/pim/file/get/5c932067280fda0001770d7f",
                "isConfNet": "N",
                "marketName": "DEEBOT 505",
                "materialNo": "20200115005",
                "model": "D505",
                "productId": "20200115064057_024db39cda0d9f092563c364f62c5b50",
            },
        ],
        "moreHelpModuleList": [],
    }


def help_product_index() -> HelpProductIndex:
    """Return the help of a product."""
    url_01 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20230428010042_1bc8d9bd2ee5a7e7b7956654db4062b0&lang=EN"
    url_02 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_cd763556564ff0a61fc41d2624908891&lang=EN"
    url_03 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_3657ef5c16da7cbcaab698b21fb2ecc0&lang=EN"
    url_04 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_0e70117dde190eb6dce3b6244e79d517&lang=EN"
    url_05 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_cb47cb63c80300bef9cc3db74950fcd7&lang=EN"
    url_06 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200324010022_8aabbbfc0d85e9d1a031a1417ff27fb8&lang=EN"
    url_07 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200115064101_4bbc5047c0f483044342546bc7b63df2&lang=EN"
    url_08 = f"https://{bumper_isc.DOMAIN_SEC3}/product/faq?faqId=20200115064101_6cc9eae8d3e4d8cd5a9429e43a1e2474&lang=EN"
    url_09 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20Android.mp4"
    url_10 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20Android.mp4"
    url_11 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20connect%20ECOVACS%20Home%20App-for%20iOS.mp4"
    url_12 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20pair%20smart%20home%20device-Amazon%20Echo.mp4"
    url_13 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20pair%20smart%20home%20device-Google%20Home.mp4"
    url_14 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20start%20using%20your%20Ecovacs%20robot.mp4"
    url_15 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/Learn%20more%20features%20with%20ECOVACS%20Home%20App.mp4"
    url_16 = f"https://{bumper_isc.DOMAIN_ALIYUN}/Universal%20video/How%20to%20use%20Smart%20Navi3.0.mp4"
    view_url = (
        f"https://{bumper_isc.DOMAIN_SEC3}"
        "/product/instructions?instructionsId=20200115064102_39366488ec99d1980b7da5ae5e414994&lang=EN"
    )
    title_07 = (
        "I forgot my Ecovacs account number and password,"
        " but when I click “Forgot password” I don't receive an authentication email. What should I do?"
    )

    return {
        "faqResponse": {
            "faqList": [
                {
                    "faqId": "20230428010042_1bc8d9bd2ee5a7e7b7956654db4062b0",
                    "title": "How to disassemble the mopping plate?",
                    "url": url_01,
                },
                {
                    "faqId": "20200324010022_cd763556564ff0a61fc41d2624908891",
                    "title": "Making your first map with your OZMO 920 / 950",
                    "url": url_02,
                },
                {
                    "faqId": "20200324010022_3657ef5c16da7cbcaab698b21fb2ecc0",
                    "title": "Continuous Cleaning Feature on your OZMO 920 / 950",
                    "url": url_03,
                },
                {
                    "faqId": "20200324010022_0e70117dde190eb6dce3b6244e79d517",
                    "title": "Virtual Boundaries with your OZMO 920 / 950",
                    "url": url_04,
                },
                {
                    "faqId": "20200324010022_cb47cb63c80300bef9cc3db74950fcd7",
                    "title": "Losing and Recovering Maps",
                    "url": url_05,
                },
                {
                    "faqId": "20200324010022_8aabbbfc0d85e9d1a031a1417ff27fb8",
                    "title": "What's the difference between the OZMO 920 and the OZMO 950?",
                    "url": url_06,
                },
                {
                    "faqId": "20200115064101_4bbc5047c0f483044342546bc7b63df2",
                    "title": title_07,
                    "url": url_07,
                },
                {
                    "faqId": "20200115064101_6cc9eae8d3e4d8cd5a9429e43a1e2474",
                    "title": "DEEBOT is cleaning with a louder noise than normal. What should I do?",
                    "url": url_08,
                },
            ],
            "hasMore": "Y",
        },
        "headImgResponse": {"clickAction": "", "clickURL": None, "headImgUrl": None, "params": {}},
        "instructions": {
            "downloadUrl": f"https://{bumper_isc.DOMAIN_ALIYUN}/OZMO950/DX9GDEESFRITRU.pdf",
            "viewUrl": view_url,
        },
        "productResponse": {
            "imgUrl": f"https://{pim_host()}/api/pim/file/get/606278df4a84d700082b39f1",
            "marketName": "DEEBOT OZMO 950 Series",
            "materialNo": "110-1820-0101",
            "model": "DX9G",
            "productId": "20200115064101_c871daa7c1cb74f447d4fcdb38040eaf",
        },
        "skillsResponse": None,
        "videoList": [
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1b9bf024120001a329a1",
                "url": url_09,
                "videoId": "20200115064102_53712c13629a24d93f1dfeeb414dbe0e",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1b9d1ec5e60001e80ede",
                "url": url_10,
                "videoId": "20200115064102_d8c1d0a45ee63a9d4e4220cc78c00f67",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1ca01ec5e60001e80edf",
                "url": url_11,
                "videoId": "20200115064102_a8ea7077bd83ba24d15b65471adbbad7",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1ce81ec5e60001e80ee4",
                "url": url_12,
                "videoId": "20200115064102_224e23c73bc9d351036cebe732e9a169",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1d0b1ec5e60001e80ee5",
                "url": url_13,
                "videoId": "20200115064102_eedca6a77557529138b667912ced1281",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1d631ec5e60001e80ee9",
                "url": url_14,
                "videoId": "20200115064102_9d6cbb0901c268c3df8ab60f95fe56d7",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1d901ec5e60001e80eec",
                "url": url_15,
                "videoId": "20200115064102_d794f817dc24ae9b379c7edfa0bb7c4e",
            },
            {
                "coverImgUrl": f"https://{pim_host()}/api/pim/file/get/5e1d1dc11ec5e60001e80ef1",
                "url": url_16,
                "videoId": "20200115064102_160366390cc2205aeb20515674ddd4ec",
            },
        ],
    }
