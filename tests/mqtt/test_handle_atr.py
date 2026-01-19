import json
from typing import Any

import pytest

from bumper.db import clean_log_repo
from bumper.mqtt.handle_atr import clean_log
from bumper.utils.utils import to_int


@pytest.mark.usefixtures("clean_database")
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("", 0),
        (None, 0),
        (1, 0),
        ("TEST", 0),
        ([], 0),
        ({}, 0),
        ({"body": {}}, 0),
        ({"body": {"data": {}}}, 0),
        ({"body": {"data": {"cid": "123"}}}, 0),
        ({"body": {"data": {"cid": "111", "start": "1768213516382"}}}, 0),
        ({"body": {"data": {"cid": "123", "start": "1768213516382"}}}, 1),
        (
            {
                "body": {
                    "data": {
                        "cid": "123",
                        "start": "1768213516382",
                        "area": "1337",
                        "time": "10",
                        "stopReason": "1",
                        "type": "auto",
                    },
                },
            },
            1,
        ),
    ],
)
def test_clean_log(payload: dict[str, Any], expected: int) -> None:
    did = "test_device"
    rid = "test_rid"

    assert len(clean_log_repo.list_by_did(did)) == 0
    clean_log(did, rid, json.dumps(payload))
    saved_logs = clean_log_repo.list_by_did(did)
    assert len(saved_logs) == expected

    if expected == 0:
        return
    start_p = payload.get("body", {}).get("data", {}).get("start")
    assert saved_logs[0].clean_log_id == f"{did}@{start_p}@{rid}"
    assert saved_logs[0].area == to_int(payload.get("body", {}).get("data", {}).get("area"))
    assert saved_logs[0].last == to_int(payload.get("body", {}).get("data", {}).get("time"))
    assert saved_logs[0].stop_reason == to_int(payload.get("body", {}).get("data", {}).get("stopReason"))
    assert saved_logs[0].ts == to_int(start_p)
    assert saved_logs[0].type == payload.get("body", {}).get("data", {}).get("type")
