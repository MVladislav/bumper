"""Helper bot handle atr."""

import json
import logging

from bumper.db import clean_log_repo
from bumper.utils.utils import to_int
from bumper.web.utils.models import CleanLog

_LOGGER = logging.getLogger(__name__)


def clean_log(did: str, rid: str, payload: str, *, event_type: str | None = None) -> None:
    """Add clean log.

    Accepts ongoing stats and the final stats event. The final event's header
    timestamp supplies the wall-clock end when the data body omits it.
    """
    _LOGGER.debug(f"CLEAN_LOG :: DID: {did} :: RID: {rid} :: PAYLOAD: {payload}")
    res = json.loads(payload)
    if not isinstance(res, dict):
        return

    body_data = res.get("body", {}).get("data")
    if not isinstance(body_data, dict):
        return

    body_data = dict(body_data)
    if event_type == "onLastTimeStats" and body_data.get("end") is None:
        header = res.get("header")
        timestamp = to_int(header.get("ts")) if isinstance(header, dict) else None
        if timestamp is not None:
            body_data["end"] = _timestamp_seconds(timestamp)

    if (cid := body_data.get("cid")) is None:
        return
    if cid == "111":
        return
    if body_data.get("start") is None:
        return

    t_clean_log = CleanLog.from_dict(did=did, rid=rid, data=body_data)
    clean_log_repo.add_or_update(t_clean_log)


def _timestamp_seconds(timestamp: int) -> int:
    """Convert a robot timestamp in seconds, milliseconds, or nanoseconds to seconds."""
    if timestamp >= 100_000_000_000_000_000:
        return timestamp // 1_000_000_000
    if timestamp >= 100_000_000_000_000:
        return timestamp // 1_000_000
    if timestamp >= 100_000_000_000:
        return timestamp // 1_000
    return timestamp
