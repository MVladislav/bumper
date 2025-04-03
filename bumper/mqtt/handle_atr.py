"""Helper bot handle atr."""

import json
import logging

from bumper.utils import db, utils
from bumper.web.models import CleanLog

_LOGGER = logging.getLogger(__name__)


def clean_log(did: str, rid: str, payload: str) -> None:
    """Add clean log.

    type: "onStats" or "reportStats"
    """
    try:
        _LOGGER.debug(f"{did} :: {payload}")
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
        if (start := body_data.get("start")) is None:
            return

        t_clean_log = CleanLog(f"{did}@{start}@{rid}")
        # t_clean_log.aiavoid =
        # t_clean_log.aitypes =
        t_clean_log.area = body_data.get("area")
        # t_clean_log.image_url =
        t_clean_log.last = body_data.get("time")
        t_clean_log.stop_reason = body_data.get("stopReason")
        t_clean_log.ts = start
        t_clean_log.type = body_data.get("type")

        # stop = body.get("stop") # if the clean is started (0) or stopped (1)
        # map_count = body.get("mapCount")
        # content = body.get("content")

        db.clean_log_add(did, cid, t_clean_log)
    except Exception:
        _LOGGER.exception(utils.default_exception_str_builder(info="during handle clean_log"))
