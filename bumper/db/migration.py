"""Manage clean log entries."""

from datetime import datetime
import logging
import shutil

from tinydb import TinyDB

from bumper.utils.errors import MigrationError
from bumper.utils.settings import config as bumper_isc

from .db import TABLE_CLEAN_LOGS, get_db, get_db_version, set_db_version

_LOGGER = logging.getLogger(__name__)


def migrate_db() -> None:
    """Perform database migrations to the latest version."""
    db = get_db()
    version = get_db_version() or "0.0.0"

    try:
        while version in MIGRATIONS:
            next_version, fn = MIGRATIONS[version]
            _LOGGER.info(f"Starting database migration :: {version} → {next_version}")
            backup_file = _backup_db()
            _LOGGER.info(f"Database backup created :: {backup_file}")
            fn(db)
            set_db_version(next_version)
            version = next_version
            _LOGGER.info(f"Database migration completed :: now at version {version}")

        if version != bumper_isc.APP_VERSION:
            set_db_version()
            _LOGGER.info(f"Database version aligned with application :: {version} → {bumper_isc.APP_VERSION}")
            version = bumper_isc.APP_VERSION
    except Exception:
        _LOGGER.exception("Database migration failed")
        raise


def _backup_db() -> str:
    """Create a timestamped backup of the database and return its filename."""
    ts = datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).strftime("%Y%m%d-%H%M%S")
    backup_file = f"{bumper_isc.db_file}.bak.{ts}"
    shutil.copy(bumper_isc.db_file, backup_file)
    return backup_file


def _migrate_clean_logs_0_2_2_to_0_2_3(db: TinyDB) -> None:
    """Flatten clean_logs nested lists into individual documents."""
    table = db.table(TABLE_CLEAN_LOGS)
    new_entries = []

    # old schema: each doc has "logs": [...]
    for doc in table.all():
        logs = doc.get("logs")
        if logs is None:
            continue
        if not isinstance(logs, list):
            msg = "Invalid clean_logs schema: logs is not a list"
            raise MigrationError(msg)

        for log in logs:
            if not isinstance(log, dict):
                msg = "Invalid clean_logs entry"
                raise MigrationError(msg)
            # Flatten
            log_copy = log.copy()
            log_copy["did"] = doc.get("did")
            new_entries.append(log_copy)

    # clear old table and insert flattened entries
    table.truncate()
    table.insert_multiple(new_entries)


MIGRATIONS = {
    "0.0.0": ("0.2.3", _migrate_clean_logs_0_2_2_to_0_2_3),
    "0.2.2": ("0.2.3", _migrate_clean_logs_0_2_2_to_0_2_3),
}
