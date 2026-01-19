"""Models module."""

from datetime import datetime
from typing import Any

from bumper.utils.settings import config as bumper_isc
from bumper.utils.utils import to_int


class VacBotDevice:
    """Vacuum bot device."""

    def __init__(
        self,
        did: str = "",
        class_id: str = "",
        resource: str = "",
        name: str = "",
        nick: str = "",
        company: str = "",
    ) -> None:
        """Vacuum bot device init."""
        self.class_id = class_id
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
            "class": self.class_id,
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
        bot.class_id = data.get("class", "")
        bot.company = data.get("company", "")
        bot.name = data.get("name", "")
        bot.nick = data.get("nick", "")
        bot.resource = data.get("resource", "")
        bot.mqtt_connection = data.get("mqtt_connection", False)
        bot.xmpp_connection = data.get("xmpp_connection", False)
        return bot


class VacBotClient:
    """Vacuum client."""

    def __init__(self, name: str = "", userid: str = "", realm: str = "", resource: str = "") -> None:
        """Vacuum client init."""
        self.userid = userid
        self.name = name
        self.realm = realm
        self.resource = resource
        self.mqtt_connection = False
        self.xmpp_connection = False

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "userid": self.userid,
            "name": self.name,
            "realm": self.realm,
            "resource": self.resource,
            "mqtt_connection": self.mqtt_connection,
            "xmpp_connection": self.xmpp_connection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VacBotClient":
        """Create a VacBotClient instance from a dictionary."""
        bot = cls(
            userid=data.get("userid", ""),
            name=data.get("name", ""),
            realm=data.get("realm", ""),
            resource=data.get("resource", ""),
        )
        bot.mqtt_connection = data.get("mqtt_connection", False)
        bot.xmpp_connection = data.get("xmpp_connection", False)
        return bot


class BumperUser:
    """Bumper user."""

    def __init__(self, userid: str = "") -> None:
        """Bumper user init."""
        self.userid: str = userid
        self.username: str = bumper_isc.USER_USERNAME_DEFAULT
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
        user.username = data.get("username", bumper_isc.USER_USERNAME_DEFAULT)
        user.homeids = data.get("homeids", [])
        user.devices = data.get("devices", [])
        user.bots = data.get("bots", [])
        return user


class Token:
    """User authentication token."""

    def __init__(
        self,
        userid: str,
        token: str,
        expiration: datetime,
        auth_code: str | None = None,
        it_token: str | None = None,
    ) -> None:
        self.userid = userid
        self.token = token
        self.expiration = expiration
        self.auth_code = auth_code
        self.it_token = it_token

    def to_db(self) -> dict[str, Any]:
        """Convert Token to a TinyDB-compatible dict."""
        return {
            "userid": self.userid,
            "token": self.token,
            "expiration": self.expiration.isoformat(),
            "auth_code": self.auth_code,
            "it_token": self.it_token,
        }

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "userid": self.userid,
            "token": self.token,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Token":
        """Instantiate a Token from a database dict."""
        expiration = datetime.fromisoformat(data.get("expiration", ""))
        return cls(
            userid=data.get("userid", ""),
            token=data.get("token", ""),
            expiration=expiration,
            auth_code=data.get("auth_code"),
            it_token=data.get("it_token"),
        )


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

    did: str | None = None
    cid: str | None = None
    # Older and Newer Bots
    aiavoid: int = 0
    aitypes: list[Any] = []
    area: int | None = None
    image_url: str | None = None
    stop_reason: int | None = None
    last: int | None = None  # time
    ts: int | None = None  # start
    type: str | None = None

    # Newer Bots
    avoid_count: int | None = None
    enable_power_mop: int | None = None
    power_mop_type: int | None = None
    ai_open: int | None = None
    # aq:int|None = None
    # cleanId:str|None = None
    # cornerDeep:int|None = None
    # mapName:str|None = None
    # sceneName:int|None = None
    # triggerMode:int|None = None

    def __init__(self, clean_log_id: str) -> None:
        """Clean log init."""
        self.clean_log_id = clean_log_id

    def to_db(self) -> dict[str, Any]:
        """Convert for db."""
        return self.__dict__

    @classmethod
    def from_db(cls, data: dict[str, Any]) -> "CleanLog":
        """Create a CleanLog instance from a dictionary."""
        clean_log = cls(clean_log_id=data["clean_log_id"])
        clean_log.did = data.get("did")
        clean_log.cid = data.get("cid")
        # Older and Newer Bots
        clean_log.aiavoid = to_int(data.get("aiavoid")) or 0
        clean_log.aitypes = data.get("aitypes", [])
        clean_log.area = to_int(data.get("area"))
        clean_log.image_url = data.get("image_url")
        clean_log.stop_reason = to_int(data.get("stop_reason"))
        clean_log.last = to_int(data.get("last"))
        clean_log.ts = to_int(data.get("ts"))
        clean_log.type = data.get("type")
        # Newer Bots
        clean_log.avoid_count = to_int(data.get("avoid_count"))
        clean_log.enable_power_mop = to_int(data.get("enable_power_mop"))
        clean_log.power_mop_type = to_int(data.get("power_mop_type"))
        clean_log.ai_open = to_int(data.get("ai_open"))
        return clean_log

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.clean_log_id,
            # "did": self.did,
            # "cid": self.cid,
            # Older and Newer Bots
            "aiavoid": self.aiavoid,
            "aitypes": self.aitypes,
            "area": self.area,
            "imageUrl": self.image_url if self.image_url is not None else "",
            "stopReason": self.stop_reason if self.stop_reason is not None else -2,
            "last": self.last,
            "ts": self.ts,
            "type": self.type,
            # Newer Bots
            "avoidCount": self.avoid_count,
            "enablePowerMop": self.enable_power_mop,
            "powerMopType": self.power_mop_type,
            "aiopen": self.ai_open,
        }

    @classmethod
    def from_dict(cls, did: str, rid: str, data: dict[str, Any]) -> "CleanLog":
        """Create a CleanLog instance from a dictionary."""
        start = data.get("start")
        clean_log = cls(clean_log_id=f"{did}@{start}@{rid}")
        clean_log.did = did
        clean_log.cid = data.get("cid")

        # Older and Newer Bots
        clean_log.aiavoid = data.get("aiavoid", 0)
        clean_log.aitypes = data.get("aitypes", [])
        clean_log.area = data.get("area")
        clean_log.image_url = data.get("imageUrl")
        clean_log.stop_reason = data.get("stopReason")
        clean_log.last = data.get("time")
        clean_log.ts = start
        clean_log.type = data.get("type")
        # Newer Bots
        clean_log.avoid_count = data.get("avoidCount")
        clean_log.enable_power_mop = data.get("enablePowerMop")
        clean_log.power_mop_type = data.get("powerMopType")
        clean_log.ai_open = data.get("aiopen")

        # stop = body.get("stop") # if the clean is started (0) or stopped (1)
        # map_count = body.get("mapCount")
        # content = body.get("content")

        return clean_log
