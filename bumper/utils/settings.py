"""Confi module."""

import os
from pathlib import Path
import socket
from typing import TYPE_CHECKING, Optional
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
    # bumper_dir: str = f"{os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))}/../../"
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

    # Listeners
    bumper_listen: str | None = os.environ.get("BUMPER_LISTEN", socket.gethostbyname(socket.gethostname()))
    bumper_announce_ip: str | None = os.environ.get("BUMPER_ANNOUNCE_IP", bumper_listen)

    # Logging
    bumper_level: str = (os.environ.get("BUMPER_DEBUG_LEVEL") or "INFO").upper()
    bumper_verbose: int = int(os.environ.get("BUMPER_DEBUG_VERBOSE") or 1)
    DEBUG_LOGGING_API_REQUEST: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST")) or False
    DEBUG_LOGGING_API_REQUEST_MISSING: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_REQUEST_MISSING")) or False
    DEBUG_LOGGING_XMPP_REQUEST: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST")) or False
    DEBUG_LOGGING_XMPP_REQUEST_REFACTOR: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_REQUEST_REFACTOR")) or False
    DEBUG_LOGGING_XMPP_RESPONSE: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_XMPP_RESPONSE")) or False
    DEBUG_LOGGING_API_ROUTE: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_API_ROUTE")) or False
    DEBUG_LOGGING_SA_RESULT: bool = str_to_bool(os.environ.get("DEBUG_LOGGING_SA_RESULT")) or False

    # Other
    USE_AUTH: bool = False
    TOKEN_VALIDITY_SECONDS: int = 3600  # 1 hour
    OAUTH_VALIDITY_DAYS: int = 15
    BUMPER_PROXY_MQTT: bool = str_to_bool(os.environ.get("BUMPER_PROXY_MQTT")) or False
    BUMPER_PROXY_WEB: bool = str_to_bool(os.environ.get("BUMPER_PROXY_WEB")) or False

    # Proxy
    PROXY_NAMESERVER: list[str] = ["1.1.1.1", "8.8.8.8"]
    PROXY_MQTT_DOMAIN: str = "mq-ww.ecouser.net"

    # Ports
    WEB_SERVER_TLS_LISTEN_PORT: int = int(os.environ.get("WEB_SERVER_HTTPS_PORT") or 443)
    WEB_SERVER_LISTEN_PORT: int = 8007
    MQTT_LISTEN_PORT: int = 1883
    MQTT_LISTEN_PORT_TLS: int = 8883
    XMPP_LISTEN_PORT: int = 1223
    XMPP_LISTEN_PORT_TLS: int = 5223

    # Servers
    mqtt_server: Optional["MQTTServer"] = None
    mqtt_helperbot: Optional["MQTTHelperBot"] = None
    web_server: Optional["WebServer"] = None
    xmpp_server: Optional["XMPPServer"] = None

    # Used for maintenance loop stop
    shutting_down: bool = False

    HOME_ID: str = "781a0733923f2240cf304757"


config: Config = Config()
