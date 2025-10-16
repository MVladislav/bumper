"""Manage clean log entries."""

import logging
from typing import Any

from tinydb.table import Document

from bumper.web import models

from .base import BaseRepo
from .db import TABLE_CLEAN_LOGS, query_instance
from .helpers import warn_if_not_doc

_LOGGER = logging.getLogger(__name__)


class CleanLogRepo(BaseRepo):
    """DAO for clean logs."""

    def __init__(self) -> None:
        super().__init__(TABLE_CLEAN_LOGS)

    def add(self, did: str, cid: str, log: models.CleanLog) -> None:
        """Add or update a clean log entry (ensures uniqueness based on ID, TS, and type)."""
        q = query_instance.did == did  # & (QueryInstance.cid == cid)
        entry = self._get(q)

        logs: list[dict[str, Any]] = []
        if isinstance(entry, dict | Document):
            logs = entry.get("logs", [])

            for raw in logs:
                if raw.get("clean_log_id") == log.clean_log_id and raw.get("ts") == log.ts and raw.get("type") == log.type:
                    raw.update(log.to_db())  # Update in-place
                    break
            else:
                logs.append(log.to_db())  # Append if not matched
        else:
            logs = [log.to_db()]  # New entry

        self._upsert({"did": did, "cid": cid, "logs": logs}, q)

    def list_by_did(self, did: str) -> list[models.CleanLog]:
        """List clean logs by device ID."""
        results: list[models.CleanLog] = []
        for entry in self.table.search(query_instance.did == did):
            warn_if_not_doc(entry, "CleanLogRepo.list_by_did entry")
            results.extend(models.CleanLog.from_db(raw) for raw in entry.get("logs", []))
        return results

    def clear(self) -> None:
        """Clear all clean logs."""
        self.table.truncate()

    def remove_by_id(self, clean_log_id: str) -> None:
        """Remove a clean log entry by its clean_log_id."""
        did = clean_log_id.split("@", 1)[0]
        entries = self.table.search(query_instance.did == did)

        for entry in entries:
            warn_if_not_doc(entry, "CleanLogRepo.remove_by_id entry")
            logs = entry.get("logs", [])
            updated_logs = [log for log in logs if log.get("clean_log_id") != clean_log_id]

            # Only update if logs were actually removed
            if len(logs) != len(updated_logs):
                q = (query_instance.did == entry["did"]) & (query_instance.cid == entry["cid"])
                self._upsert({"logs": updated_logs}, q)
