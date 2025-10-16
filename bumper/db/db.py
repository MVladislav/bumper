"""Initialize TinyDB connection and define table constants."""

from tinydb import Query, TinyDB

from bumper.utils.settings import config as bumper_isc

# Table names
TABLE_BOTS = "bots"
TABLE_USERS = "users"
TABLE_CLIENTS = "clients"

TABLE_TOKENS = "tokens"

TABLE_CLEAN_LOGS = "clean_logs"


# Shared Query instance for TinyDB queries
query_instance = Query()


def get_db() -> TinyDB:
    """Return initialized TinyDB instance with all tables created."""
    db = TinyDB(bumper_isc.db_file)
    for name in (TABLE_USERS, TABLE_TOKENS, TABLE_CLEAN_LOGS, TABLE_CLIENTS, TABLE_BOTS):
        db.table(name, cache_size=0)
    return db
