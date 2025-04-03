"""Models module."""

from datetime import datetime, timedelta
from typing import Any
import uuid

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc


class VacBotDevice:
    """Vacuum bot device."""

    def __init__(
        self,
        did: str = "",
        vac_bot_device_class: str = "",
        resource: str = "",
        name: str = "",
        nick: str = "",
        company: str = "",
    ) -> None:
        """Vacuum bot device init."""
        self.vac_bot_device_class = vac_bot_device_class
        self.company = company
        self.did = did
        self.name = name
        self.nick = nick
        self.resource = resource
        self.mqtt_connection = False
        self.xmpp_connection = False

    def as_dict(self) -> dict[str, str | bool]:
        """Convert to dict."""
        return {
            "class": self.vac_bot_device_class,
            "company": self.company,
            "did": self.did,
            "name": self.name,
            "nick": self.nick,
            "resource": self.resource,
            "mqtt_connection": self.mqtt_connection,
            "xmpp_connection": self.xmpp_connection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VacBotDevice":
        """Create a VacBotDevice instance from a dictionary."""
        bot = cls(did=data.get("did", ""))
        bot.vac_bot_device_class = data.get("vac_bot_device_class", "")
        bot.company = data.get("company", "")
        bot.name = data.get("name", "")
        bot.nick = data.get("nick", "")
        bot.resource = data.get("resource", "")
        bot.mqtt_connection = data.get("mqtt_connection", False)
        bot.xmpp_connection = data.get("xmpp_connection", False)
        return bot


class BumperUser:
    """Bumper user."""

    def __init__(self, userid: str = "") -> None:
        """Bumper user init."""
        self.userid: str = userid
        self.username: str = "bumper"
        self.homeids: list[str] = []
        self.devices: list[str] = []
        self.bots: list[str] = []

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "userid": self.userid,
            "username": self.username,
            "homeids": self.homeids,
            "devices": self.devices,
            "bots": self.bots,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BumperUser":
        """Create a BumperUser instance from a dictionary."""
        user = cls(userid=data.get("userid", ""))
        user.username = data.get("username", "bumper")
        user.homeids = data.get("homeids", [])
        user.devices = data.get("devices", [])
        user.bots = data.get("bots", [])
        return user


class GlobalVacBotDevice(VacBotDevice):
    """Global Vacuum Bot Device."""

    UILogicId: str = ""
    ota: bool = True
    updateInfo: dict[str, Any] = {"changeLog": "", "needUpdate": False}  # noqa: N815
    icon: str = ""
    deviceName: str = ""  # noqa: N815


class VacBotClient:
    """Vacuum client."""

    def __init__(self, userid: str = "", realm: str = "", token: str = "") -> None:
        """Vacuum client init."""
        self.userid = userid
        self.realm = realm
        self.resource = token
        self.mqtt_connection = False
        self.xmpp_connection = False

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "userid": self.userid,
            "realm": self.realm,
            "resource": self.resource,
            "mqtt_connection": self.mqtt_connection,
            "xmpp_connection": self.xmpp_connection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VacBotClient":
        """Create a VacBotClient instance from a dictionary."""
        bot = cls(userid=data.get("userid", ""), realm=data.get("realm", ""), token=data.get("token", ""))
        bot.mqtt_connection = data.get("mqtt_connection", False)
        bot.xmpp_connection = data.get("xmpp_connection", False)
        return bot


class OAuth:
    """Oauth."""

    access_token: str = ""
    expire_at: str = ""
    refresh_token: str = ""
    userId: str = ""  # noqa: N815

    def __init__(self, **entries: str) -> None:
        """Oauth init."""
        self.__dict__.update(entries)

    @classmethod
    def create_new(cls, user_id: str) -> "OAuth":
        """Create new."""
        oauth = OAuth()
        oauth.userId = user_id  # pylint: disable=invalid-name
        oauth.access_token = uuid.uuid4().hex
        oauth.expire_at = f"{datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(days=bumper_isc.OAUTH_VALIDITY_DAYS)}"
        oauth.refresh_token = uuid.uuid4().hex
        return oauth

    def to_db(self) -> dict[str, Any]:
        """Convert for db."""
        return self.__dict__

    def to_response(self) -> dict[str, Any]:
        """Convert to response."""
        data = self.__dict__
        data["expire_at"] = utils.convert_to_millis(datetime.fromisoformat(self.expire_at).timestamp())
        return data


class CleanLogs:
    """Clean logs."""

    logs: list["CleanLog"] = []

    def __init__(self, did: str, cid: str) -> None:
        """Clean logs init."""
        self.did = did
        self.cid = cid

    def to_db(self) -> dict[str, Any]:
        """Convert for db."""
        return self.__dict__


class CleanLog:
    """Clean log."""

    # NEW and OLD bots
    aiavoid: int = 0
    aitypes: list[Any] = []
    area: int | None = None
    image_url: str | None = None
    stop_reason: int | None = None
    last: int | None = None
    ts: int | None = None
    type: str | None = None

    # # Only NEW bots
    # aiopen:int|None = None
    # aq:int|None = None
    # cleanId:str|None = None
    # cornerDeep:int|None = None
    # enablePowerMop:int|None = None
    # mapName:str|None = None
    # powerMopType:int|None = None
    # sceneName:int|None = None
    # triggerMode:int|None = None

    def __init__(self, clean_log_id: str) -> None:
        """Clean log init."""
        self.clean_log_id = clean_log_id

    def to_db(self) -> dict[str, Any]:
        """Convert for db."""
        return self.__dict__

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "aiavoid": self.aiavoid,
            "aitypes": self.aitypes,
            "area": self.area,
            "id": self.clean_log_id,
            "imageUrl": self.image_url if self.image_url is not None else "",
            "last": self.last,
            "stopReason": self.stop_reason if self.stop_reason is not None else -2,
            "ts": self.ts,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CleanLog":
        """Create a CleanLog instance from a dictionary."""
        clean_log = cls(clean_log_id=data["clean_log_id"])
        clean_log.aiavoid = data.get("aiavoid", 0)
        clean_log.aitypes = data.get("aitypes", [])
        clean_log.area = data.get("area")
        clean_log.image_url = data.get("image_url")
        clean_log.last = data.get("last")
        clean_log.stop_reason = data.get("stop_reason")
        clean_log.ts = data.get("ts")
        clean_log.type = data.get("type")
        return clean_log


RETURN_API_SUCCESS = "0000"
ERR_ACTIVATE_TOKEN_TIMEOUT = "1006"  # noqa: S105
ERR_COMMON = "0001"
ERR_DEFAULT = "9000"
ERR_EMAIL_NON_EXIST = "1002"
ERR_EMAIL_SEND_TIME_LIMIT = "1011"
ERR_EMAIL_USED = "1001"
ERR_INTERFACE_AUTH = "0002"
ERR_PARAM_INVALID = "0003"
ERR_PWD_WRONG = "1005"  # noqa: S105
ERR_RESET_PWD_TOKEN_TIMEOUT = "1007"  # noqa: S105
ERR_TIMESTAMP_INVALID = "0005"
ERR_TOKEN_INVALID = "0004"  # noqa: S105
ERR_USER_DISABLE = "1004"
ERR_USER_NOT_ACTIVATED = "1003"
ERR_WRONG_COMFIRM_PWD = "10010"  # noqa: S105
ERR_WRONG_EMAIL_ADDRESS = "1008"
ERR_WRONG_PWD_FROMATE = "1009"  # noqa: S105
ERR_UNKOWN_TODO = "1202"

API_ERRORS: dict[str, str] = {
    RETURN_API_SUCCESS: "0000",
    ERR_ACTIVATE_TOKEN_TIMEOUT: "1006",
    ERR_COMMON: "0001",
    ERR_DEFAULT: "9000",
    ERR_EMAIL_NON_EXIST: "1002",
    ERR_EMAIL_SEND_TIME_LIMIT: "1011",
    ERR_EMAIL_USED: "1001",
    ERR_INTERFACE_AUTH: "0002",
    ERR_PARAM_INVALID: "0003",
    ERR_PWD_WRONG: "1005",
    ERR_RESET_PWD_TOKEN_TIMEOUT: "1007",
    ERR_TIMESTAMP_INVALID: "0005",
    ERR_TOKEN_INVALID: "0004",
    ERR_USER_DISABLE: "1004",
    ERR_USER_NOT_ACTIVATED: "1003",
    ERR_WRONG_COMFIRM_PWD: "10010",
    ERR_WRONG_EMAIL_ADDRESS: "1008",
    ERR_WRONG_PWD_FROMATE: "1009",
}
