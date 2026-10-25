"""Runtime configuration for Bumper.

Every setting is an attribute of the ``Config`` singleton, so callers and tests
can replace a value without reading the environment again. Deployment-specific
values are read from the environment here; the rest are protocol constants.
"""

import asyncio
from importlib.metadata import version
import logging
import os
from pathlib import Path
import socket
from typing import TYPE_CHECKING, Literal, cast
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bumper.mqtt.helper_bot import MQTTHelperBot
    from bumper.mqtt.server import MQTTServer
    from bumper.web.server import WebServer
    from bumper.xmpp.xmpp import XMPPServer

KeyType = Literal["ec", "rsa"]


def str_to_bool(value: str | int | bool | None) -> bool:
    """Convert str to bool."""
    return str(value).lower() in ["true", "1", "t", "y", "on", "yes"]


def _debug_level() -> str:
    """Return the configured log level, accepting the old variable name."""
    if (value := os.environ.get("DEBUG_BUMPER_LEVEL")) is None and (value := os.environ.get("BUMPER_DEBUG_LEVEL")) is not None:
        _LOGGER.warning("BUMPER_DEBUG_LEVEL is deprecated; use DEBUG_BUMPER_LEVEL")
    return (value or "INFO").upper()


def _debug_verbose() -> int:
    """Return the configured log detail, accepting the old variable name."""
    value = os.environ.get("DEBUG_BUMPER_VERBOSE")
    if value is None and (value := os.environ.get("BUMPER_DEBUG_VERBOSE")) is not None:
        _LOGGER.warning("BUMPER_DEBUG_VERBOSE is deprecated; use DEBUG_BUMPER_VERBOSE")
    return int(value or 1)


class Config:
    """The runtime configuration of this Bumper instance."""

    # defaults -----------------------------------------------------------------
    ECOVACS_DEFAULT_COUNTRY: str = "us"
    ECOVACS_DEFAULT_COUNTRY_LANG: str = "en"
    LOCAL_TIMEZONE: ZoneInfo = ZoneInfo(os.environ.get("TZ", "UTC"))
    SYNC_TIMEZONE: bool = str_to_bool(os.environ.get("SYNC_TIMEZONE"))

    # files --------------------------------------------------------------------
    bumper_dir = Path.cwd()
    data_dir = Path(os.environ.get("BUMPER_DATA", bumper_dir / "data"))
    certs_dir = Path(os.environ.get("BUMPER_CERTS", bumper_dir / "certs"))
    voice_dir = Path(os.environ.get("BUMPER_VOICES", data_dir / "voices"))
    codepush_dir = Path(os.environ.get("BUMPER_CODEPUSH", data_dir / "codepush"))
    db_file = str(Path(os.environ.get("DB_FILE") or data_dir / "bumper.db"))
    account_key_file = Path(os.environ.get("BUMPER_ACCOUNT_KEY", data_dir / "account.key"))

    # The default directories are created on import. Tests replace the paths before the server starts.
    for _directory in (data_dir, certs_dir, voice_dir, codepush_dir):
        _directory.mkdir(parents=True, exist_ok=True)
    del _directory

    # TLS ----------------------------------------------------------------------
    ca_cert = Path(os.environ.get("BUMPER_CA_CERT") or os.environ.get("BUMPER_CA") or certs_dir / "ca.crt")
    ca_key = Path(os.environ.get("BUMPER_CA_KEY", certs_dir / "ca.key"))
    ca_pem = Path(os.environ.get("BUMPER_CA_PEM", certs_dir / "ca.pem"))
    server_cert = Path(os.environ.get("BUMPER_CERT", certs_dir / "bumper.crt"))
    server_key = Path(os.environ.get("BUMPER_KEY", certs_dir / "bumper.key"))
    ca_archive_filename = "ca-certificates.tar.gz"
    CA_CERT_API_ONLY_BUMPER_CERT: bool = str_to_bool(os.environ.get("CA_CERT_API_ONLY_BUMPER_CERT"))
    ca_valid_days = int(os.environ.get("BUMPER_CA_VALID_DAYS") or 6669)
    server_valid_days = int(os.environ.get("BUMPER_VALID_DAYS") or 666)
    cert_key_type: KeyType = cast("KeyType", (os.environ.get("CERT_KEY_TYPE") or "ec").lower())
    cert_rsa_key_size: int = int(os.environ.get("CERT_RSA_KEY_SIZE") or 2048)

    if os.environ.get("BUMPER_CA") is not None and os.environ.get("BUMPER_CA_CERT") is None:
        _LOGGER.warning("BUMPER_CA is deprecated; use BUMPER_CA_CERT")

    # listeners ----------------------------------------------------------------
    bumper_listen: str | None = os.environ.get("BUMPER_LISTEN", socket.gethostbyname(socket.gethostname()))
    bumper_announce_ip: str | None = os.environ.get("BUMPER_ANNOUNCE_IP", bumper_listen)
    WEB_SERVER_TLS_LISTEN_PORT: int = int(os.environ.get("WEB_SERVER_HTTPS_PORT") or 443)
    WEB_SERVER_LISTEN_PORT: int = int(os.environ.get("WEB_SERVER_LISTEN_PORT") or 8007)
    MQTT_LISTEN_PORT: int = int(os.environ.get("MQTT_LISTEN_PORT") or 1883)
    MQTT_LISTEN_PORT_TLS: int = int(os.environ.get("MQTT_LISTEN_PORT_TLS") or 8883)
    # XMPP_LISTEN_PORT: int = int(os.environ.get("XMPP_LISTEN_PORT") or 1223)
    XMPP_LISTEN_PORT_TLS: int = int(os.environ.get("XMPP_LISTEN_PORT_TLS") or 5223)

    # logging ------------------------------------------------------------------
    debug_bumper_level: str = _debug_level()
    debug_bumper_verbose: int = _debug_verbose()
    DEBUG_LOGGING_API_REQUEST: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST"))
    DEBUG_LOGGING_API_REQUEST_MISSING: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST_MISSING"))
    DEBUG_LOGGING_XMPP_REQUEST_ORIGINAL: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST"))
    DEBUG_LOGGING_XMPP_REQUEST_REFACTORED: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST_REFACTOR"))
    DEBUG_LOGGING_XMPP_RESPONSE: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_RESPONSE"))
    DEBUG_LOGGING_SA_RESULT: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_SA_RESULT"))

    # auth ---------------------------------------------------------------------
    # Request signatures are not verified. This switch only gates the token
    # and auth-code checks in the MQTT and XMPP servers.
    USE_AUTH: bool = False
    TOKEN_VALIDITY_SECONDS: int = int(os.environ.get("TOKEN_VALIDITY_SECONDS", "2592000"))  # 30 days
    ACCESS_TOKEN_VALIDITY_SECONDS: int = int(os.environ.get("ACCESS_TOKEN_VALIDITY_SECONDS", "1800"))  # 30 minutes
    REFRESH_TOKEN_VALIDITY_SECONDS: int = int(os.environ.get("REFRESH_TOKEN_VALIDITY_SECONDS", "2592000"))  # 30 days
    DEVICE_OTP_TTL_SECONDS: int = 120
    EMAIL_VERIFY_CODE: str = "666666"
    TOKEN_JWT_ALG: str = os.environ.get("TOKEN_JWT_ALG") or ("RS256" if cert_key_type == "rsa" else "ES256")

    # proxy --------------------------------------------------------------------
    BUMPER_PROXY_MQTT: bool = str_to_bool(os.environ.get("BUMPER_PROXY_MQTT"))
    BUMPER_PROXY_WEB: bool = str_to_bool(os.environ.get("BUMPER_PROXY_WEB"))
    PROXY_NAMESERVERS: list[str] = ["1.1.1.1", "8.8.8.8"]
    PROXY_MQTT_DOMAIN: str = "mq-ww.ecouser.net"
    PROXY_PUBLISH_TIMEOUT: float = float(os.environ.get("PROXY_PUBLISH_TIMEOUT") or 10.0)
    HELPER_BOT_TIMEOUT: float = float(os.environ.get("HELPER_BOT_TIMEOUT") or 10.0)

    # hosts --------------------------------------------------------------------
    DOMAIN_ALIYUN: str = "globalapp-eu.oss-eu-central-1.aliyuncs.com"
    DOMAIN_MAIN: str = "ecouser.net"
    DOM_SUB_1: str = ""  # "dc-eu.ww."
    DOM_SUB_2: str = ""  # "dc.ww."
    DOM_SUB_3: str = ""  # "area.ww."
    DOMAIN_SEC: str = "ecovacs.com"
    DOMAIN_SEC1 = DOMAIN_SEC  # f"www.{DOMAIN_SEC}"
    DOMAIN_SEC2 = DOMAIN_SEC  # f"gl-us-pub.{DOMAIN_SEC}"
    DOMAIN_SEC3 = DOMAIN_SEC  # f"gl-us-wap.{DOMAIN_SEC}"
    DOMAIN_SEC4 = DOMAIN_SEC  # f"club-eu-wap.{DOMAIN_SEC}"
    DOMAIN_SEC5 = DOMAIN_SEC  # f"sa-us-datasink.{DOMAIN_SEC}"
    DOMAIN_SEC6 = DOMAIN_SEC  # f"bumper.{DOMAIN_SEC}"
    ECOVACS_UPDATE_SERVER: str = "3.68.172.231"  # ww: 52.53.84.66 | eu: 3.68.172.231
    ECOVACS_UPDATE_SERVER_PORT: int = 8005

    # accounts -----------------------------------------------------------------
    DEFAULT_HOME_ID: str = "781a0733923f2240cf304757"
    USER_USERNAME_DEFAULT: str = os.environ.get("USER_USERNAME_DEFAULT", "bumper")
    USER_NICKNAME_DEFAULT: str = os.environ.get("USER_NICKNAME_DEFAULT", USER_USERNAME_DEFAULT)
    USER_MAIL_DEFAULT: str = os.environ.get("USER_MAIL_DEFAULT", f"{USER_USERNAME_DEFAULT}@home.local")
    USER_CLASS_IDS: set[str] = {"ecouser", "bumper", "USER"}

    # retention ----------------------------------------------------------------
    # How many uploads of a kind are kept per device. The oldest are dropped on
    # every new upload, so the database cannot grow without bound.
    PHOTO_MAX_PER_DEVICE: int = int(os.environ.get("PHOTO_MAX_PER_DEVICE", "20"))
    CLEAN_LOG_MAX_PER_DEVICE: int = int(os.environ.get("CLEAN_LOG_MAX_PER_DEVICE", "100"))

    # webview ------------------------------------------------------------------
    # Hosts the app may open in a webview. The app ships the Ecovacs domains
    # as a fallback; add the host this instance is reached under.
    WEBVIEW_TRUSTED_HOST_SUFFIXES: tuple[str, ...] = tuple(
        suffix.strip()
        for suffix in os.environ.get(
            "WEBVIEW_TRUSTED_HOST_SUFFIXES",
            "ecovacs.com,ecovacs.cn,ecouser.net,my.site.com,force.com,salesforce-sites.com,salesforce-scrt.com",
        ).split(",")
        if suffix.strip()
    )

    # runtime ------------------------------------------------------------------
    mqtt_server: "MQTTServer | None" = None
    mqtt_helperbot: "MQTTHelperBot | None" = None
    web_server: "WebServer | None" = None
    xmpp_server: "XMPPServer | None" = None
    background_tasks: set[asyncio.Task[None]] = set()
    shutting_down: bool = False
    CODEPUSH_LOCAL_PACKAGE: bool = str_to_bool(os.environ.get("CODEPUSH_LOCAL_PACKAGE"))

    # metadata -----------------------------------------------------------------
    APP_VERSION: str = os.environ.get("VERSION_BUMPER") or version("bumper")
    GITHUB_REPO: str = "https://github.com/MVladislav/bumper"
    GITHUB_RELEASE: str = "https://github.com/MVladislav/bumper/pkgs/container/bumper"


config: Config = Config()
