"""Confi module."""

import asyncio
from importlib.metadata import version
import os
from pathlib import Path
import socket
import tempfile
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from bumper.mqtt.helper_bot import MQTTHelperBot
    from bumper.mqtt.server import MQTTServer
    from bumper.web.server import WebServer
    from bumper.xmpp.xmpp import XMPPServer


def str_to_bool(value: str | int | bool | None) -> bool:
    """Convert str to bool."""
    return str(value).lower() in ["true", "1", "t", "y", "on", "yes"]


class Config:
    """Config class."""

    ECOVACS_DEFAULT_COUNTRY: str = "us"
    LOCAL_TIMEZONE: ZoneInfo = ZoneInfo(os.environ.get("TZ", "UTC"))

    # ww: 52.53.84.66 | eu: 3.68.172.231
    ECOVACS_UPDATE_SERVER: str = "3.68.172.231"
    ECOVACS_UPDATE_SERVER_PORT: int = 8005

    # os.environ['PYTHONASYNCIODEBUG'] = '1' # Uncomment to enable ASYNCIODEBUG
    bumper_dir = Path.cwd()

    # Set defaults from environment variables first
    # Folders
    data_dir = Path(os.environ.get("BUMPER_DATA", bumper_dir / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)  # Ensure data directory exists or create

    certs_dir = Path(os.environ.get("BUMPER_CERTS", bumper_dir / "certs"))
    certs_dir.mkdir(parents=True, exist_ok=True)  # Ensure certs directory exists or create

    # Certs
    ca_cert = Path(os.environ.get("BUMPER_CA", certs_dir / "ca.crt"))
    server_cert = Path(os.environ.get("BUMPER_CERT", certs_dir / "bumper.crt"))
    server_key = Path(os.environ.get("BUMPER_KEY", certs_dir / "bumper.key"))
    ca_archive_filename = "ca-certificates.tar.gz"
    ca_archive_file = Path(tempfile.mkdtemp(prefix="bumper_ca_certificates_")) / ca_archive_filename
    CA_CERT_API_ONLY_BUMPER_CERT: bool = str_to_bool(os.environ.get("CA_CERT_API_ONLY_BUMPER_CERT")) or False

    # Data Files
    db_file = str(Path(os.environ.get("DB_FILE") or data_dir / "bumper.db"))

    # Listeners
    bumper_listen: str | None = os.environ.get("BUMPER_LISTEN", socket.gethostbyname(socket.gethostname()))
    bumper_announce_ip: str | None = os.environ.get("BUMPER_ANNOUNCE_IP", bumper_listen)

    # Logging
    debug_bumper_level: str = (os.environ.get("DEBUG_BUMPER_LEVEL") or "INFO").upper()
    debug_bumper_verbose: int = int(os.environ.get("DEBUG_BUMPER_VERBOSE") or 1)
    DEBUG_LOGGING_API_REQUEST: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST")) or False
    DEBUG_LOGGING_API_REQUEST_MISSING: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST_MISSING")) or False
    DEBUG_LOGGING_XMPP_REQUEST_ORIGINAL: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST")) or False
    DEBUG_LOGGING_XMPP_REQUEST_REFACTORED: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST_REFACTOR")) or False
    DEBUG_LOGGING_XMPP_RESPONSE: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_RESPONSE")) or False
    DEBUG_LOGGING_SA_RESULT: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_SA_RESULT")) or False

    # Other
    USE_AUTH: bool = False
    TOKEN_VALIDITY_SECONDS: int = 1800  # 30 minutes
    TOKEN_JWT_ALG: str = os.environ.get("TOKEN_JWT_ALG") or "ES256"
    BUMPER_PROXY_MQTT: bool = str_to_bool(os.environ.get("BUMPER_PROXY_MQTT")) or False
    BUMPER_PROXY_WEB: bool = str_to_bool(os.environ.get("BUMPER_PROXY_WEB")) or False

    # Proxy
    PROXY_NAMESERVER: list[str] = ["1.1.1.1", "8.8.8.8"]
    PROXY_MQTT_DOMAIN: str = "mq-ww.ecouser.net"

    # Domains
    DOMAIN_ALI: str = "globalapp-eu.oss-eu-central-1.aliyuncs.com"

    DOMAIN_MAIN: str = "ecouser.net"
    DOM_SUB_PORT: str = DOMAIN_MAIN  # f"portal-ww.{DOMAIN_MAIN}"
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

    # Ports
    WEB_SERVER_TLS_LISTEN_PORT: int = int(os.environ.get("WEB_SERVER_HTTPS_PORT") or 443)
    WEB_SERVER_LISTEN_PORT: int = int(os.environ.get("WEB_SERVER_LISTEN_PORT") or 8007)
    MQTT_LISTEN_PORT: int = int(os.environ.get("MQTT_LISTEN_PORT") or 1883)
    MQTT_LISTEN_PORT_TLS: int = int(os.environ.get("MQTT_LISTEN_PORT_TLS") or 8883)
    XMPP_LISTEN_PORT: int = int(os.environ.get("XMPP_LISTEN_PORT") or 1223)
    XMPP_LISTEN_PORT_TLS: int = int(os.environ.get("XMPP_LISTEN_PORT_TLS") or 5223)

    # Servers
    mqtt_server: "MQTTServer | None" = None
    mqtt_helperbot: "MQTTHelperBot | None" = None
    web_server: "WebServer | None" = None
    xmpp_server: "XMPPServer | None" = None

    # Services
    background_tasks: set[asyncio.Task[None]] = set()

    # Used for maintenance loop stop
    shutting_down: bool = False

    HOME_ID: str = "781a0733923f2240cf304757"
    USER_USERNAME_DEFAULT: str = "bumper"
    USER_NICKNAME_DEFAULT: str = "bumper"
    USER_MAIL_DEFAULT: str = f"{USER_USERNAME_DEFAULT}@home.local"

    USER_REALMS: set[str] = {"ecouser", "bumper", "USER"}

    # Dynamically load the application version from pyproject.toml
    APP_VERSION: str = version("bumper")
    GITHUB_REPO: str = "https://github.com/MVladislav/bumper"
    GITHUB_RELEASE: str = "https://github.com/MVladislav/bumper/pkgs/container/bumper"


config: Config = Config()
