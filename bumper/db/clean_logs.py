"""Manage clean log entries."""

import logging

from tinydb.table import Document

from bumper.utils.settings import config as bumper_isc
from bumper.utils.utils import to_int
from bumper.web.utils.models import CleanLog

from .base import BaseRepo
from .db import TABLE_CLEAN_LOGS, query_instance

_LOGGER = logging.getLogger(__name__)


class CleanLogRepo(BaseRepo):
    """DAO for clean logs."""

    def __init__(self) -> None:
        super().__init__(TABLE_CLEAN_LOGS)

    def add_or_update(self, log: CleanLog) -> None:
        """Add or update a clean log entry (ensures uniqueness based on LOG_ID, and TYPE)."""
        q = (query_instance.clean_log_id == log.clean_log_id) & (query_instance.type == log.type)
        self._upsert(log.to_db(), q)
        if log.did:
            self.prune(log.did, bumper_isc.CLEAN_LOG_MAX_PER_DEVICE)

    def prune(self, did: str, keep: int) -> None:
        """Drop all but the `keep` newest clean logs of a device."""
        records = self._get_multi(query_instance.did == did)
        ordered = sorted(records, key=lambda record: to_int(record.get("ts"), 0) or 0, reverse=True)
        for record in ordered[keep:]:
            self.table.remove(doc_ids=[record.doc_id])

    def list_by_did(self, did: str) -> list[CleanLog]:
        """List clean logs by device ID."""
        rec = self._get_multi(query_instance.did == did)
        return [CleanLog.from_db(doc) for doc in rec if isinstance(doc, dict)]

    def list_by_id(self, clean_log_id: str) -> CleanLog | None:
        """List clean logs by clean log id."""
        rec = self._get(query_instance.clean_log_id == clean_log_id)
        return CleanLog.from_db(rec) if isinstance(rec, dict | Document) else None

    def list_all(self) -> list[CleanLog]:
        """List all clean logs."""
        return [CleanLog.from_db(doc) for doc in self.table.all() if isinstance(doc, dict)]

    def clear(self) -> None:
        """Clear all clean logs."""
        self.table.truncate()

    def remove_by_id(self, clean_log_id: str) -> None:
        """Remove a clean log entry by its clean_log_id."""
        self._remove(query_instance.clean_log_id == clean_log_id)
