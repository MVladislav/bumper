"""Identifiers of an account and of the clients that use it.

One account has three names on the Ecovacs API: the account id, the unified
id, and the id of its IoT session. An app installation has a client id and a
resource. The shapes are kept in one place so every part of Bumper generates
and recognizes the same forms.
"""

from datetime import UTC, datetime
import hashlib
import re
import secrets
import string

_ACCOUNT_ID = re.compile(r"^\d{14}_[0-9a-f]{32}$")
_IOT_ID = re.compile(r"^[a-z0-9]{16}$")
_CLIENT_ID = re.compile(r"^[0-9a-f]{24}$")
_LEGACY_ID = re.compile(r"^[0-9a-f]{20}$")
_IOT_ALPHABET = string.ascii_lowercase + string.digits


def new_account_uid(created: datetime | None = None) -> str:
    """Return an account id in the shape the API uses."""
    moment = created or datetime.now(tz=UTC)
    return f"{moment:%Y%m%d%H%M%S}_{secrets.token_hex(16)}"


def new_uc_uid(created: datetime | None = None) -> str:
    """Return a unified account id in the shape the API uses."""
    return new_account_uid(created)


def new_iot_uid() -> str:
    """Return the id of an IoT session."""
    return "".join(secrets.choice(_IOT_ALPHABET) for _ in range(16))


def new_client_id() -> str:
    """Return the id of an app installation."""
    return secrets.token_hex(12)


def legacy_account_uid(account: str) -> str:
    """Return the id older Bumper versions derived from a login name.

    It is kept so a record created by an older version is still found when
    the same login name arrives again.
    """
    return hashlib.sha256(account.encode("utf-8")).hexdigest()[:20]


def is_account_uid(value: str) -> bool:
    """Return whether a value has the shape of an account or unified id."""
    return bool(_ACCOUNT_ID.fullmatch(value))


def is_iot_uid(value: str) -> bool:
    """Return whether a value has the shape of an IoT id."""
    return bool(_IOT_ID.fullmatch(value))


def is_client_id(value: str) -> bool:
    """Return whether a value has the shape of an app client id."""
    return bool(_CLIENT_ID.fullmatch(value))


def is_legacy_uid(value: str) -> bool:
    """Return whether a value has the shape of an older Bumper account id."""
    return bool(_LEGACY_ID.fullmatch(value))
