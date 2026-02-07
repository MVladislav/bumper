"""Helper bot handle atr."""

import json
import logging

from bumper.db import clean_log_repo
from bumper.web.utils.models import CleanLog

_LOGGER = logging.getLogger(__name__)


def clean_log(did: str, rid: str, payload: str) -> None:
    """Add clean log.

    type: "onStats" or "reportStats"
    """
    _LOGGER.debug(f"CLEAN_LOG :: DID: {did} :: RID: {rid} :: PAYLOAD: {payload}")
    res = json.loads(payload)
    if not isinstance(res, dict):
        return

    body_data = res.get("body", {}).get("data")
    if not isinstance(body_data, dict):
        return

    if (cid := body_data.get("cid")) is None:
        return
    if cid == "111":
        return
    if body_data.get("start") is None:
        return

    t_clean_log = CleanLog.from_dict(did=did, rid=rid, data=body_data)
    clean_log_repo.add_or_update(t_clean_log)
