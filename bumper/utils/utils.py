"""Utils module."""

import datetime
import json
import logging
from pathlib import Path
import re

import validators

from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)

# ******************************************************************************


def default_log_warn_not_impl(func: str) -> None:
    """Get default log warn for not implemented."""
    _LOGGER.debug(f"!!! POSSIBLE THIS API IS NOT (FULL) IMPLEMENTED :: {func} !!!")


def default_exception_str_builder(e: Exception | None = None, info: str | None = None) -> str:
    """Build default exception message."""
    i_error = ""
    i_info = ""
    if e is not None:
        i_error = f" :: {e}"
    if info is not None:
        i_info = f" :: {info}"
    return f"Unexpected exception occurred{i_info}{i_error}"


# ******************************************************************************


def convert_to_millis(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return round(seconds * 1000)


def get_current_time_as_millis() -> int:
    """Get current time in millis."""
    return convert_to_millis(datetime.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())


def str_to_bool(value: str | int | bool | None) -> bool:
    """Convert str to bool."""
    return str(value).lower() in ["true", "1", "t", "y", "on", "yes"]


# ******************************************************************************


def is_valid_url(url: str | None) -> bool:
    """Validate if is a url."""
    return bool(validators.url(url))


def is_valid_ip(ip: str | None) -> bool:
    """Validate if is ipv4 or ipv6."""
    return bool(validators.ipv4(ip) or validators.ipv6(ip))


# ******************************************************************************


def get_dc_code(area_code: str) -> str:
    """Return to a area code the corresponding dc code."""
    return get_area_code_map().get(area_code, "na")


def get_area_code_map() -> dict[str, str]:
    """Return area code map."""
    try:
        with Path.open(Path(__file__).parent / "utils_area_code_mapping.json", encoding="utf-8") as file:
            res = json.load(file)
            if isinstance(res, dict):
                return res
    except Exception:
        _LOGGER.warning("Could not find/read utils_area_code_mapping.json")
    return {}


def check_url_not_used(url: str) -> bool:
    """Check if a url is not in the know api list, used in the middleware for debug."""
    return any(re.search(pattern, url) for pattern in _FIND_NOT_USED_API_REQUEST)


_FIND_NOT_USED_API_REQUEST = [
    r"/api/appsvr/app.do",
    r"/api/appsvr/app/config",
    r"/api/appsvr/device/blacklist/check",
    r"/api/appsvr/improve",
    r"/api/appsvr/improve/accept",
    r"/api/appsvr/notice/home",
    r"/api/appsvr/oauth_callback",
    r"/api/appsvr/ota/firmware",
    r"/api/appsvr/service/list",
    r"/api/basis/dc/get-by-area",
    r"/api/dim/devmanager.do",
    r"/api/ecms/app/ad/res",
    r"/api/ecms/app/ad/res/v2",
    r"/api/ecms/app/element/hint",
    r"/api/ecms/app/push/event",
    r"/api/ecms/app/resources",
    r"/api/ecms/file/get/(.*?)",
    r"/api/homed/device/move",
    r"/api/homed/home/create",
    r"/api/homed/home/delete",
    r"/api/homed/home/list",
    r"/api/homed/home/update",
    r"/api/homed/member/list",
    r"/api/iot/devmanager.do",
    r"/api/lg/log.do",
    r"/api/microservice-recomend/userReminderResult/",
    r"/api/neng/message/getlist",
    r"/api/neng/message/getShareMsgs",
    r"/api/neng/message/hasUnreadMsg",
    r"/api/neng/message/read",
    r"/api/neng/v2/message/push",
    r"/api/neng/v3/message/latest_by_did",
    r"/api/neng/v3/message/list",
    r"/api/neng/v3/message/pushStatus",
    r"/api/neng/v3/product/msg/tabs",
    r"/api/neng/v3/shareMsg/hasUnreadMsg",
    r"/api/ota/products/wukong/class/(.*?)/firmware/latest.json",
    r"/api/photo/list",
    r"/api/pim/api/pim/file/get/(.*?)",
    r"/api/pim/consumable/getPurchaseUrl",
    r"/api/pim/dictionary/getErrDetail",
    r"/api/pim/file/get/(.*?)",
    r"/api/pim/product/getConfigGroups",
    r"/api/pim/product/getConfignetAll",
    r"/api/pim/product/getProductIotMap",
    r"/api/pim/product/software/config/batch",
    r"/api/pim/product/getShareInfo",
    r"/api/pim/voice/get",
    r"/api/pim/voice/getLanuages",
    r"/api/rapp/sds/user/data/del",
    r"/api/rapp/sds/user/data/map/get",
    r"/api/sds/baidu/audio/getcred",
    r"/api/users/user.do",
    r"/app/dln/api/log/clean_result/del",
    r"/app/dln/api/log/clean_result/list",
    r"/$",
    r"/bot/remove/(.*?)",
    r"/bots$",
    r"/client/remove/(.*?)",
    r"/clients$",
    r"/config/Android.conf$",
    r"/data_collect/upload/generalData$",
    r"/favicon.ico$",
    r"/list_routes$",
    r"/lookup.do$",
    r"/newauth.do$",
    r"/restart_(.*?)",
    r"/sa$",
    r"/server-status$",
    r"/static/(.*?)",
    r"/upload/global/(.*?)/(.*?)/(.*?)/(.*?)",
    r"/v1/global/auth/getAuthCode",
    r"/v1/private/(.*?)//user/getMyUserMenuInfo",
    r"/v1/private/(.*?)/ad/getAdByPositionType",
    r"/v1/private/(.*?)/ad/getBootScreen",
    r"/v1/private/(.*?)/agreement/getUserAcceptInfo",
    r"/v1/private/(.*?)/campaign/homePageAlert",
    r"/v1/private/(.*?)/common/checkAPPVersion",
    r"/v1/private/(.*?)/common/checkVersion",
    r"/v1/private/(.*?)/common/getAboutBriefItem",
    r"/v1/private/(.*?)/common/getAgreementURLBatch",
    r"/v1/private/(.*?)/common/getAreas",
    r"/v1/private/(.*?)/common/getBottomNavigateInfoList",
    r"/v1/private/(.*?)/common/getConfig",
    r"/v1/private/(.*?)/common/getCurrentAreaSupportServiceInfo",
    r"/v1/private/(.*?)/common/getSystemReminder",
    r"/v1/private/(.*?)/common/getTimestamp",
    r"/v1/private/(.*?)/common/getUserConfig",
    r"/v1/private/(.*?)/common/uploadDeviceInfo",
    r"/v1/private/(.*?)/help/getHelpIndex",
    r"/v1/private/(.*?)/help/getProductHelpIndex",
    r"/v1/private/(.*?)/intl/member/basicInfo",
    r"/v1/private/(.*?)/intl/member/signStatus",
    r"/v1/private/(.*?)/member/getExpByScene",
    r"/v1/private/(.*?)/message/getMsgList",
    r"/v1/private/(.*?)/message/hasUnreadMsg",
    r"/v1/private/(.*?)/osmall/getCountryConfig",
    r"/v1/private/(.*?)/osmall/index/getBannerList",
    r"/v1/private/(.*?)/osmall/index/getConfNetRobotPartsGoods",
    r"/v1/private/(.*?)/osmall/index/getGoodsCategory",
    r"/v1/private/(.*?)/osmall/index/getLayout",
    r"/v1/private/(.*?)/osmall/index/getRecommendGoods",
    r"/v1/private/(.*?)/osmall/proxy/cart/get-count",
    r"/v1/private/(.*?)/osmall/proxy/my/get-user-center-coupon-list",
    r"/v1/private/(.*?)/osmall/proxy/order/list",
    r"/v1/private/(.*?)/osmall/proxy/product/material-accessory-list",
    r"/v1/private/(.*?)/osmall/proxy/v2/web/benefit/get-benefits",
    r"/v1/private/(.*?)/osmall/proxy/v2/web/payment-icon/index",
    r"/v1/private/(.*?)/shop/getCnWapShopConfig",
    r"/v1/private/(.*?)/user/acceptAgreementBatch",
    r"/v1/private/(.*?)/user/changeArea",
    r"/v1/private/(.*?)/user/checkAgreement",
    r"/v1/private/(.*?)/user/checkAgreementBatch",
    r"/v1/private/(.*?)/user/checkLogin",
    r"/v1/private/(.*?)/user/getAuthCode",
    r"/v1/private/(.*?)/user/getMyUserMenuInfo",
    r"/v1/private/(.*?)/user/getUserAccountInfo",
    r"/v1/private/(.*?)/user/getUserMenuInfo",
    r"/v1/private/(.*?)/user/login",
    r"/v1/private/(.*?)/user/logout",
    r"/v1/private/(.*?)/user/queryChangeArea",
    r"/v1/private/(.*?)/userSetting/getMsgReceiveSetting",
    r"/v1/private/(.*?)/userSetting/getSuggestionSetting",
    r"/v1/private/(.*?)/userSetting/saveUserSetting",
    r"/v2/private/(.*?)/common/getBottomNavigateInfoList",
    r"/v2/private/(.*?)/member/getExpByScene",
    r"/v2/private/(.*?)/message/hasMoreUnReadMsg",
    r"/v2/private/(.*?)/message/moduleConfiguration",
    r"/v2/private/(.*?)/message/waterfallFlow",
    r"/v2/private/(.*?)/user/checkAgreementBatch",
    r"/v2/private/(.*?)/user/checkLogin",
    r"/v2/private/(.*?)/userSetting/getMsgReceiveSetting",
    r"/v3/private/(.*?)/common/getBottomNavigateInfoList",
]
