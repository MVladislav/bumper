"""Resolve the several names of one account to a single Bumper user.

The app names the same account in more than one way: the name it logs in
with, the id of its IoT session, and the id of the app installation. Bumper
keeps one user record for the account and remembers the other names as
aliases, so a lookup by any of them reaches the same record.
"""

import logging

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils.account_ids import (
    is_account_uid,
    is_iot_uid,
    legacy_account_uid,
    new_account_uid,
    new_iot_uid,
    new_uc_uid,
)
from bumper.web.jwt import verify_jwt
from bumper.web.utils.models import BumperUser

_LOGGER = logging.getLogger(__name__)


def ensure_public_ids(user: BumperUser) -> BumperUser:
    """Fill in the names the API assigns to an account.

    A record created by an older version has only the id Bumper derived from
    the login name. The account id, the unified id, and the IoT id are added
    once and kept, and every one of them is remembered as a name of the
    account, so the old id keeps resolving to the same record.
    """
    changed = False
    if not user.account_uid:
        user.account_uid = user.userid if is_account_uid(user.userid) else new_account_uid()
        changed = True
    if not user.uc_uid:
        user.uc_uid = new_uc_uid()
        changed = True
    if not user.iot_uid:
        user.iot_uid = user.userid if is_iot_uid(user.userid) else new_iot_uid()
        changed = True

    aliases = list(user.aliases)
    for value in (user.account_uid, user.uc_uid, user.iot_uid):
        if value and value != user.userid and value not in aliases:
            aliases.append(value)
            changed = True
    if not changed:
        return user

    user.aliases = aliases
    user_repo.set_identity(user)
    return user_repo.get_by_id(user.userid) or user


def create_account(login_name: str, username: str | None = None, email: str | None = None) -> BumperUser:
    """Create an account for a login name and return it.

    The login name is resolved first, so a second request with the same name
    returns the account that already exists instead of a duplicate.
    """
    if (existing := resolve_login(login_name)) is not None:
        return ensure_public_ids(existing)
    user = user_repo.create(login_name, username=username, email=email)
    reconcile_bot_owners()
    return user_repo.get_by_id(user.userid) or user


def resolve_login(login_name: str | None) -> BumperUser | None:
    """Resolve the name a client logs in with to one account.

    New records store the login name. A record from an older version stored
    only the hash of the name, so that hash is tried as well. An old record's
    login name is stored when it is resolved; its public ids are assigned by
    the caller after any presented ids have had a chance to be adopted.
    """
    if not login_name:
        return None

    user = user_repo.get_by_login_name(login_name)
    if user is None:
        user = user_repo.get_by_id(legacy_account_uid(login_name))
    if user is None:
        user = user_repo.get_by_id(login_name)
    if user is None:
        return None

    if not user.login_name:
        user_repo.set_login_name(user.userid, login_name)
        user = user_repo.get_by_id(user.userid) or user
    return user


def adopt_public_id(user: BumperUser, value: str | None, *, kind: str = "account") -> BumperUser:
    """Remember an id the client presents for an account.

    The account id and the IoT id have different shapes. A value of the
    expected shape fills the matching field when it is empty; otherwise it is
    kept only as a name. A value without a known shape is kept as a name.
    """
    if not value or value == user.userid or value in user.aliases:
        return user

    changed = False
    if kind == "account" and is_account_uid(value) and not user.account_uid:
        user.account_uid = value
        changed = True
    elif is_iot_uid(value) and not user.iot_uid:
        user.iot_uid = value
        changed = True
    elif is_account_uid(value) and not user.account_uid:
        user.account_uid = value
        changed = True

    aliases = list(user.aliases)
    if value not in aliases:
        aliases.append(value)
        changed = True
    if not changed:
        return user

    user.aliases = aliases
    user_repo.set_identity(user)
    return user_repo.get_by_id(user.userid) or user


def resolve_user(
    user_id: str | None = None,
    *,
    device_id: str | None = None,
    token_user_id: str | None = None,
    prefer_device: bool = False,
) -> BumperUser | None:
    """Resolve an account name, an app device, or a token user to one user.

    The token user is the name Bumper issued the token for, so it wins over a
    name a request supplies. When the caller prefers the device, the account
    bound to the app installation wins first, because that is the account the
    installation logged in with. The device is the fallback otherwise. Every
    other name that points at the resolved user is remembered as an alias.
    """
    user: BumperUser | None = None
    if prefer_device and device_id:
        user = user_repo.get_by_device_id(device_id)
    if user is None and token_user_id:
        user = user_repo.get_by_id(token_user_id)
    if user is None and user_id:
        user = user_repo.get_by_id(user_id)
    if user is None and device_id:
        user = user_repo.get_by_device_id(device_id)
    if user is None:
        return None

    if token_user_id and token_user_id != user.userid:
        user = adopt_public_id(user, token_user_id, kind="iot")
        user = adopt_alias(user, token_user_id)
    if user_id and user_id != user.userid:
        user = adopt_public_id(user, user_id)
        user = adopt_alias(user, user_id)
    return user


def adopt_alias(user: BumperUser, alias: str) -> BumperUser:
    """Remember another name of an account, merging a duplicate record.

    A record that already answers to the alias is the same account when the
    caller has linked the two, either through a token or through an app device.
    Its devices, robots, homes, tokens, and clients move to the older record, so
    a name the app used earlier does not stay a second user. The older record
    keeps its own id; the name that was adopted is stored only as an alias.
    """
    if not alias or alias == user.userid:
        return user

    user = ensure_public_ids(user)
    other = user_repo.get_by_id(alias)
    if other is not None and other.userid != user.userid:
        _LOGGER.info("Merging a duplicate account record")
        other = ensure_public_ids(other)
        user, removed_user_id = user_repo.merge(user, other)
        token_repo.reassign_user(removed_user_id, user.userid)
        client_repo.reassign_user(removed_user_id, user.userid)
        user = ensure_public_ids(user)

    user_repo.add_alias(user.userid, alias)
    return user_repo.get_by_id(user.userid) or user


def verify_transport_secret(user_id: str, secret: str | None) -> bool:
    """Return whether a transport secret was issued for the account.

    A secret is one of the values Bumper hands out: the portal token, the auth
    code, the IT token, or a signed access token. A JWT is only accepted when
    its signature and expiry check out and it is an access token.
    """
    if not secret:
        return False
    target = user_repo.get_by_id(user_id)
    if target is None:
        return False

    if (token := token_repo.get_valid_by_secret(secret)) is not None:
        token_user = user_repo.get_by_id(token.userid)
        if token_user is not None and token_user.userid == target.userid:
            return True

    details = verify_jwt(secret)
    if details is None:
        return False
    jwt_user_id = details.get("user_id")
    if not isinstance(jwt_user_id, str):
        return False
    jwt_user = user_repo.get_by_id(jwt_user_id)
    return jwt_user is not None and jwt_user.userid == target.userid


def resolve_transport_user(transport_id: str, secret: str | None) -> BumperUser | None:
    """Resolve the name a transport presents to the account that owns it.

    The secret is one of the values the app received for the account: the
    portal token, the auth code, the IT token, or a signed access token. It is
    the link between the name the transport uses and the account, so a
    transport that still carries an older name does not become a second client.
    A token is only trusted when its signature and expiry check out, even when
    `USE_AUTH` is off, because resolving by a claim can move an account.
    """
    token_user_id: str | None = None
    if secret:
        if (token := token_repo.get_valid_by_secret(secret)) is not None:
            token_user_id = token.userid
        elif (details := verify_jwt(secret)) is not None and isinstance(details.get("user_id"), str):
            token_user_id = details["user_id"]

    user = resolve_user(transport_id, token_user_id=token_user_id)
    if user is not None and transport_id != user.userid:
        user = adopt_alias(user, transport_id)
    return user


def reconcile_users() -> None:
    """Merge the records that name the same account.

    Two records can only be one account when they share an app installation
    or a login name. The older record keeps its id, and the tokens and clients
    of the other record move to it before the other record is removed. The
    merged record is given the public names when it does not have them yet.
    """
    while (pair := _find_duplicate()) is not None:
        first, second = pair
        merged, removed_user_id = user_repo.merge(first, second)
        if not removed_user_id:
            break
        token_repo.reassign_user(removed_user_id, merged.userid)
        client_repo.reassign_user(removed_user_id, merged.userid)
        ensure_public_ids(merged)
        _LOGGER.info("Merged duplicate account records")


def _find_duplicate() -> tuple[BumperUser, BumperUser] | None:
    """Return two records that name the same account."""
    return _find_shared_public_id() or _find_shared_device() or _find_shared_login_name()


def _find_shared_public_id() -> tuple[BumperUser, BumperUser] | None:
    """Return two users that carry the same public id or known alias."""
    owners: dict[str, BumperUser] = {}
    for user in user_repo.list_all():
        for value in user.names:
            if (owner := owners.get(value)) is not None and owner.userid != user.userid:
                return owner, user
            owners[value] = user
    return None


def _find_shared_device() -> tuple[BumperUser, BumperUser] | None:
    """Return two users that carry the same app device."""
    owners: dict[str, BumperUser] = {}
    for user in user_repo.list_all():
        for device_id in user.devices:
            if (owner := owners.get(device_id)) is not None and owner.userid != user.userid:
                return owner, user
            owners[device_id] = user
    return None


def _find_shared_login_name() -> tuple[BumperUser, BumperUser] | None:
    """Return two users that log in with the same name."""
    owners: dict[str, BumperUser] = {}
    for user in user_repo.list_all():
        if not user.login_name:
            continue
        key = user.login_name.casefold()
        if (owner := owners.get(key)) is not None and owner.userid != user.userid:
            return owner, user
        owners[key] = user
    return None


def assign_bot_to_all_users(device_id: str) -> None:
    """Give a known robot to every local account."""
    if not device_id:
        return
    for user in user_repo.list_all():
        if device_id not in user.bots:
            user_repo.add_bot(user.userid, device_id)


def reconcile_bot_owners() -> None:
    """Give every known robot to every local account.

    Bumper has no account invitation or robot-sharing flow. The local accounts
    therefore share the robot inventory, including accounts and robots created
    at different times.
    """
    for bot in bot_repo.list_all():
        assign_bot_to_all_users(bot.did)
