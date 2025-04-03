"""Database module."""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB, where
from tinydb.queries import QueryInstance
from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc
from bumper.web import models

_LOGGER = logging.getLogger(__name__)


TABLE_USERS = "users"
TABLE_CLIENTS = "clients"
TABLE_BOTS = "bots"
TABLE_TOKENS = "tokens"
TABLE_OAUTH = "oauth"
TABLE_CLEAN_LOGS = "clean_logs"

User_Query = Query()


def _db_get() -> TinyDB:
    # Will create the database if it doesn't exist
    db = TinyDB(_db_file())

    # Will create the tables if they don't exist
    db.table(TABLE_USERS, cache_size=0)
    db.table(TABLE_CLIENTS, cache_size=0)
    db.table(TABLE_BOTS, cache_size=0)
    db.table(TABLE_TOKENS, cache_size=0)
    db.table(TABLE_OAUTH, cache_size=0)
    db.table(TABLE_CLEAN_LOGS, cache_size=0)

    return db


def _db_file() -> str:
    return os.environ.get("DB_FILE") or _os_db_path()


def _os_db_path() -> str:  # createdir=True):
    return str(Path(bumper_isc.data_dir) / "bumper.db")


def _logging_message_not_document(value: Document | list[Document] | None, value_name: str) -> str:
    """Log Helper for generic not a Document info."""
    return f"'{value_name}' is not a 'Document' => {type(value)}"


# ******************************************************************************
#
# LOGS HANDLER
#
# ******************************************************************************


def clean_log_add(did: str, cid: str, log: models.CleanLog) -> None:
    """Add new clean log."""
    _update_clean_logs_list_field(did, cid, log, add=True)


def clean_log_by_id(did: str) -> list[models.CleanLog]:
    """Get clean logs by did."""
    clean_log_data: list[models.CleanLog] = []
    with _db_get() as db:
        clean_logs = db.table(TABLE_CLEAN_LOGS)
        t_clean_logs = clean_logs.search(User_Query.did == did)
        for t_clean_log in t_clean_logs:
            logs = t_clean_log.get("logs", [])
            clean_log_data.extend(models.CleanLog.from_dict(log) for log in logs)
    return clean_log_data


def _update_clean_logs_list_field(did: str, cid: str, clean_log: models.CleanLog, add: bool) -> None:
    """Help function to add or remove an item from a clean log list."""
    with _db_get() as db:
        clean_logs = db.table(TABLE_CLEAN_LOGS)
        t_clean_log = clean_logs.get(User_Query.did == did and User_Query.cid == cid)

        # if no clean log was saved before, create a new empty list
        if t_clean_log is None:
            _clean_logs_add(did, cid)
            t_clean_log = clean_logs.get(User_Query.did == did and User_Query.cid == cid)

        # updated clean logs
        if isinstance(t_clean_log, Document):
            clean_log_logs = list(t_clean_log.get("logs", []))
            is_saved = _check_clean_log_saved(clean_log_logs, clean_log)
            # Add because not saved
            if add and is_saved is False:
                clean_log_logs.append(clean_log.to_db())
            # Update saved one
            elif add and is_saved is True:
                pass  # nothing todo, as it will updated in _check_clean_log_saved
            # Remove saved one
            elif not add and is_saved is True:
                clean_log_logs.remove(clean_log.to_db())
            clean_logs.upsert({"logs": clean_log_logs}, User_Query.did == did and User_Query.cid == cid)
        elif t_clean_log is not None:
            _LOGGER.warning(_logging_message_not_document(t_clean_log, "t_clean_log"))


def _check_clean_log_saved(clean_log_logs: list[dict[str, Any]], clean_log: models.CleanLog) -> bool:
    for clean_log_log in clean_log_logs:
        t_clean_log_log = models.CleanLog.from_dict(clean_log_log)
        if (
            t_clean_log_log.clean_log_id == clean_log.clean_log_id
            and t_clean_log_log.ts == clean_log.ts
            and t_clean_log_log.type == clean_log.type
        ):
            clean_log_log.update(clean_log.to_db())
            return True
    return False


def _clean_logs_add(did: str, cid: str) -> None:
    """Add new empty clean log entry."""
    with _db_get() as db:
        new_clean_log = models.CleanLogs(did, cid)
        clean_logs = db.table(TABLE_CLEAN_LOGS)
        t_clean_log = clean_logs.get(User_Query.did == did and User_Query.cid == cid)

        if t_clean_log is None:
            _LOGGER.info(f"Adding new clean log with did: {did} and cid: {cid}")
            clean_logs.upsert(new_clean_log.to_db(), User_Query.did == did and User_Query.cid == cid)


def clean_logs_clean() -> None:
    """Clean all logs."""
    with _db_get() as db:
        db.table(TABLE_CLEAN_LOGS).truncate()


# ******************************************************************************
#
# USER HANDLER
#
# ******************************************************************************

# ==> ADDs


def user_add(user_id: str) -> None:
    """Add new user."""
    new_user = models.BumperUser(userid=user_id)
    user = user_by_user_id(user_id)

    if user is None:
        _LOGGER.info(f"Adding new user with userid: {new_user.userid}")
        _user_full_upsert(new_user)


def _user_full_upsert(user: models.BumperUser) -> None:
    with _db_get() as db:
        users = db.table(TABLE_USERS)
        users.upsert(user.as_dict(), User_Query.did == user.userid)
        user_add_home(user.userid, bumper_isc.HOME_ID)


# ==> GETTER


def user_by_user_id(user_id: str) -> models.BumperUser | None:
    """Get user by user id."""
    return _get_user(User_Query.userid == user_id)


def user_by_device_id(device_id: str) -> models.BumperUser | None:
    """Get user by device id."""
    return _get_user(User_Query.devices.any([device_id]))


def user_by_home_id(home_id: str) -> models.BumperUser | None:
    """Get user by home id."""
    return _get_user(User_Query.homeids.any([home_id]))


def _get_user(query: QueryInstance) -> models.BumperUser | None:
    """Help function to get an user."""
    with _db_get() as db:
        users = db.table(TABLE_USERS)
        user_data = users.get(query)
        if isinstance(user_data, Document):
            return models.BumperUser.from_dict(user_data)
        if user_data is not None:
            _LOGGER.warning(_logging_message_not_document(user_data, "user_data"))
    return None


# ==> ADD/REMOVE DEVICE|BOT|HOME


def user_add_device(user_id: str, did: str) -> None:
    """Add device to user."""
    _update_list_field(user_id, "devices", did, add=True)


def user_remove_device(user_id: str, did: str) -> None:
    """Remove device from user."""
    _update_list_field(user_id, "devices", did, add=False)


def user_add_bot(user_id: str, did: str) -> None:
    """Add bot to user."""
    _update_list_field(user_id, "bots", did, add=True)


def user_remove_bot(user_id: str, did: str) -> None:
    """Remove bot from user."""
    _update_list_field(user_id, "bots", did, add=False)


def user_add_home(user_id: str, home_id: str) -> None:
    """Add home to user."""
    _update_list_field(user_id, "homeids", home_id, add=True)


def user_remove_home(user_id: str, home_id: str) -> None:
    """Remove home from user."""
    _update_list_field(user_id, "homeids", home_id, add=False)


def _update_list_field(user_id: str, field_name: str, value: str, add: bool) -> None:
    """Help function to add or remove an item from a list field."""
    with _db_get() as db:
        users = db.table(TABLE_USERS)
        t_user = users.get(User_Query.userid == user_id)
        if isinstance(t_user, Document):
            user_list = list(t_user.get(field_name, []))
            if add and value not in user_list:
                user_list.append(value)
            elif not add and value in user_list:
                user_list.remove(value)
            users.upsert({field_name: user_list}, User_Query.userid == user_id)
        elif t_user is not None:
            _LOGGER.warning(_logging_message_not_document(t_user, "t_user"))


# ******************************************************************************
#
# TOKEN HANDLER
#
# ******************************************************************************


def user_add_token(user_id: str, token: str) -> None:
    """Add token for given user if not exists."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        t_token = tokens.get((User_Query.userid == user_id) & (User_Query.token == token))
        if t_token is None:
            _LOGGER.debug(f"Adding token {token} for userid {user_id}")
            tokens.insert(
                {
                    "userid": user_id,
                    "token": token,
                    "expiration": str(
                        datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=bumper_isc.TOKEN_VALIDITY_SECONDS),
                    ),
                },
            )


def user_get_token(user_id: str, token: str) -> Document | None:
    """Get token by user."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        t_token = tokens.get((User_Query.userid == user_id) & (User_Query.token == token))
        if isinstance(t_token, Document):
            return t_token
        if t_token is not None:
            _LOGGER.warning(_logging_message_not_document(t_token, "t_token"))
    return None


def user_get_token_v2(user_id: str) -> Document | None:
    """Get token by user."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        t_token = tokens.get(User_Query.userid == user_id)
        if isinstance(t_token, Document):
            return t_token
        if t_token is not None:
            _LOGGER.warning(_logging_message_not_document(t_token, "t_token"))
    return None


def check_token(uid: str, token: str) -> bool:
    """Check token."""
    _LOGGER.debug(f"Checking for token: {token}")
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        return bool(tokens.contains((User_Query.token == token) & (User_Query.userid == uid)))


def user_add_auth_code(user_id: str, token: str, auth_code: str) -> None:
    """Add user authcode."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        token_query = (User_Query.userid == user_id) & (User_Query.token == token)
        if tokens.contains(token_query):
            tokens.update({"authcode": auth_code}, token_query)


def user_add_auth_code_v2(user_id: str, auth_code: str) -> None:
    """Add user authcode."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        if tokens.contains(User_Query.userid == user_id):
            tokens.update({"authcode": auth_code}, User_Query.userid == user_id)


def token_by_auth_code(auth_code: str) -> Document | None:
    """Get token by authcode."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        t_auth = tokens.get(User_Query.authcode == auth_code)
        if isinstance(t_auth, Document):
            return t_auth
        if t_auth is not None:
            _LOGGER.warning(_logging_message_not_document(t_auth, "t_token"))
    return None


def check_auth_code(uid: str, auth_code: str) -> bool:
    """Check authcode."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        return bool(tokens.contains((User_Query.authcode == auth_code) & (User_Query.userid == uid)))


def login_by_it_token(auth_code: str) -> dict[str, Any] | None:
    """Login by token."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        t_auth = tokens.get(User_Query.authcode == auth_code)
        if isinstance(t_auth, Document):
            return {"token": t_auth.get("token"), "userid": t_auth.get("userid")}
        if t_auth is not None:
            _LOGGER.warning(_logging_message_not_document(t_auth, "t_token"))
    return None


def user_revoke_expired_tokens(user_id: str) -> None:
    """Revoke expired user tokens."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        expired_tokens = tokens.search(
            (User_Query.userid == user_id) & (where("expiration") < str(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE))),
        )

        for token_doc in expired_tokens:
            _LOGGER.debug(f"Removing token {token_doc.get('token')} due to expiration")
            tokens.remove(doc_ids=[token_doc.doc_id])


def user_revoke_token(user_id: str, token: str) -> None:
    """Revoke user token."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        tokens.remove((User_Query.userid == user_id) & (User_Query.token == token))


def revoke_expired_tokens() -> None:
    """Revoke expired tokens."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        expired_tokens = tokens.search(where("expiration") < str(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)))

        for token_doc in expired_tokens:
            _LOGGER.debug(f"Removing token {token_doc.get('token')} due to expiration")
            tokens.remove(doc_ids=[token_doc.doc_id])


# ******************************************************************************
#
# OAUTH HANDLER
#
# ******************************************************************************


def user_add_oauth(user_id: str) -> models.OAuth | None:
    """Add oauth for user."""
    user_revoke_expired_oauths(user_id)
    with _db_get() as db:
        oauth_table = db.table(TABLE_OAUTH)
        entry = oauth_table.get(User_Query.userid == user_id)
        if isinstance(entry, Document):
            return models.OAuth(**entry)
        if entry is None:
            oauth = models.OAuth.create_new(user_id)
            _LOGGER.debug(f"Adding oauth {oauth.access_token} for userid {user_id}")
            oauth_table.insert(oauth.to_db())
            return oauth
        _LOGGER.warning(_logging_message_not_document(entry, "entry"))
    return None


def user_revoke_expired_oauths(user_id: str) -> None:
    """Revoke expired oauths by user."""
    with _db_get() as db:
        oauth_table = db.table(TABLE_OAUTH)
        expired_oauths = oauth_table.search(
            (User_Query.userid == user_id) & (where("expire_at") < str(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE))),
        )

        for oauth_doc in expired_oauths:
            _LOGGER.debug(f"Removing oauth {oauth_doc.get('access_token')} due to expiration")
            oauth_table.remove(doc_ids=[oauth_doc.doc_id])


def user_id_by_token(token: str) -> str | None:
    """Get user by token id."""
    with _db_get() as db:
        oauth_table = db.table(TABLE_OAUTH)
        t_oauth = oauth_table.get(User_Query.access_token == token)
        if isinstance(t_oauth, Document):
            return t_oauth.get("userId")
        if t_oauth is not None:
            _LOGGER.warning(_logging_message_not_document(t_oauth, "t_oauth"))
    return None


def revoke_expired_oauths() -> None:
    """Revoke expired oauths."""
    with _db_get() as db:
        oauth_table = db.table(TABLE_OAUTH)
        expired_oauths = oauth_table.search(where("expire_at") < str(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE)))

        for oauth_doc in expired_oauths:
            _LOGGER.debug(f"Removing oauth {oauth_doc.get('access_token')} due to expiration")
            oauth_table.remove(doc_ids=[oauth_doc.doc_id])


# ******************************************************************************
#
# CLIENTS HANDLER
#
# ******************************************************************************


def client_add(user_id: str, realm: str, resource: str) -> None:
    """Add client."""
    new_client = models.VacBotClient(userid=user_id, realm=realm)
    new_client.resource = resource

    existing_client = client_get(resource)
    if existing_client is None:
        _LOGGER.info(f"Adding new client with resource {new_client.resource}")
        _client_full_upsert(new_client)


def _client_full_upsert(client: models.VacBotClient) -> None:
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        clients.upsert(client.as_dict(), User_Query.resource == client.resource)


def client_get(resource: str) -> Document | None:
    """Get client by resource."""
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        t_client = clients.get(User_Query.resource == resource)
        if isinstance(t_client, Document):
            return t_client
        if t_client is not None:
            _LOGGER.warning(_logging_message_not_document(t_client, "t_client"))
    return None


def client_get_all() -> list[Document]:
    """Get all bots."""
    return _db_get().table(TABLE_CLIENTS).all()


def get_disconnected_xmpp_clients() -> list[Document]:
    """Get disconnected XMPP clients."""
    clients = _db_get().table(TABLE_CLIENTS)
    # pylint: disable-next=singleton-comparison
    return clients.search(User_Query.xmpp_connection == False)  # noqa: E712


def client_remove(resource: str) -> None:
    """Remove client."""
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        t_client = client_get(resource)
        if t_client is not None:
            clients.remove(doc_ids=[t_client.doc_id])


def client_set_mqtt(resource: str | None, mqtt: bool) -> None:
    """Client set MQTT status."""
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        clients.upsert({"mqtt_connection": mqtt}, User_Query.resource == resource)


def client_set_xmpp(resource: str | None, xmpp: bool) -> None:
    """Client set XMPP status."""
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        clients.upsert({"xmpp_connection": xmpp}, User_Query.resource == resource)


def client_reset_connection_status() -> None:
    """Reset all client connection status."""
    with _db_get() as db:
        clients = db.table(TABLE_CLIENTS)
        for client in clients:
            client_set_mqtt(client.get("resource"), False)
            client_set_xmpp(client.get("resource"), False)


# ******************************************************************************
#
# BOTS HANDLER
#
# ******************************************************************************


def bot_add(sn: str, did: str, dev_class: str, resource: str, company: str) -> None:
    """Add bot."""
    new_bot = models.VacBotDevice(did=did, name=sn, resource=resource, company=company)
    new_bot.vac_bot_device_class = dev_class

    existing_bot = bot_get(did)
    # Not existing bot in database
    # AND try to prevent bad additions to the bot list
    if existing_bot is None and (dev_class != "" or "@" not in sn or "tmp" not in sn):
        _LOGGER.info(f"Adding new bot with SN: {new_bot.name} DID: {new_bot.did}")
        bot_full_upsert(new_bot)


def bot_full_upsert(vacbot: models.VacBotDevice) -> None:
    """Upsert bot."""
    with _db_get() as db:
        bots = db.table(TABLE_BOTS)
        if vacbot.did is not None and vacbot.did != "":
            bots.upsert(vacbot.as_dict(), User_Query.did == vacbot.did)
        else:
            _LOGGER.error(f"No DID in vacbot :: {vacbot}")


def bot_get_all() -> list[Document]:
    """Get all bots."""
    return _db_get().table(TABLE_BOTS).all()


def bot_remove(did: str) -> None:
    """Remove bot."""
    with _db_get() as db:
        bots = db.table(TABLE_BOTS)
        t_bot = bot_get(did)
        if t_bot is not None:
            bots.remove(doc_ids=[t_bot.doc_id])


def bot_get(did: str) -> Document | None:
    """Get bot."""
    with _db_get() as db:
        bots = db.table(TABLE_BOTS)
        t_bot = bots.get(User_Query.did == did)
        if isinstance(t_bot, Document):
            return t_bot
        if t_bot is not None:
            _LOGGER.warning(_logging_message_not_document(t_bot, "t_bot"))
    return None


def bot_set_nick(did: str | None, nick: str | None) -> None:
    """Bot set nickname."""
    _update_bot_field(did, "nick", nick)


def bot_set_mqtt(did: str | None, mqtt: bool) -> None:
    """Bot ste MQTT status."""
    _update_bot_field(did, "mqtt_connection", mqtt)


def bot_set_xmpp(did: str | None, xmpp: bool) -> None:
    """Bot set XMPP status."""
    _update_bot_field(did, "xmpp_connection", xmpp)


def bot_reset_connection_status() -> None:
    """Reset all bot connection status."""
    with _db_get() as db:
        bots = db.table(TABLE_BOTS)
        for bot in bots:
            _update_bot_field(bot.get("did"), "mqtt_connection", False)
            _update_bot_field(bot.get("did"), "xmpp_connection", False)


def _update_bot_field(did: str | None, field_name: str, value: Any) -> None:
    with _db_get() as db:
        bots = db.table(TABLE_BOTS)
        bots.upsert({field_name: value}, User_Query.did == did)


# ******************************************************************************
#
# TESTS HANDLER
#
# ******************************************************************************


def user_revoke_auth_code(user_id: str, token: str) -> None:
    """Revoke user authcode."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        auth_token = tokens.get((User_Query.userid == user_id) & (User_Query.token == token))
        if auth_token:
            tokens.update({"authcode": ""}, (User_Query.userid == user_id) & (User_Query.token == token))


def user_get_tokens(user_id: str) -> list[Document]:
    """Get all tokens by given user."""
    tokens = _db_get().table(TABLE_TOKENS)
    return tokens.search(User_Query.userid == user_id)


def user_revoke_all_tokens(user_id: str) -> None:
    """Revoke all tokens for given user."""
    with _db_get() as db:
        tokens = db.table(TABLE_TOKENS)
        user_tokens = tokens.search(User_Query.userid == user_id)
        tokens.remove(doc_ids=[token.doc_id for token in user_tokens])
