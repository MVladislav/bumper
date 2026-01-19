"""Initialize TinyDB connection and define table constants."""

from tinydb import Query, TinyDB
from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc

# Table names
TABLE_BOTS = "bots"
TABLE_USERS = "users"
TABLE_CLIENTS = "clients"

TABLE_TOKENS = "tokens"

TABLE_CLEAN_LOGS = "clean_logs"

TABLE_META = "_meta"

# Shared Query instance for TinyDB queries
query_instance = Query()


def get_db() -> TinyDB:
    """Return initialized TinyDB instance with all tables created."""
    db = TinyDB(bumper_isc.db_file)
    for name in (TABLE_USERS, TABLE_TOKENS, TABLE_CLEAN_LOGS, TABLE_CLIENTS, TABLE_BOTS):
        db.table(name, cache_size=0)
    return db


def get_db_version() -> str | None:
    """Return DB version."""
    db = get_db()
    meta = db.table(TABLE_META).get(Query().key == "db_version")
    return meta.get("value") if meta and isinstance(meta, dict | Document) else None


def set_db_version(version: str = bumper_isc.APP_VERSION) -> None:
    """Set DB version."""
    db = get_db()
    db.table(TABLE_META).upsert({"key": "db_version", "value": version}, Query().key == "db_version")
