import pytest

from bumper.db import clean_log_repo
from bumper.web.utils.models import CleanLog


@pytest.mark.usefixtures("clean_database")
def test_clean_logs_db() -> None:
    did = "saocsa8c9basv"
    cid = "1699297517"
    start = 1699297517
    rid = "sdu9"
    clean_log = CleanLog(f"{did}@{start}@{rid}")
    clean_log.did = did
    clean_log.cid = cid
    clean_log.area = 28
    clean_log.last = 1699297517
    clean_log.stop_reason = 1
    clean_log.ts = start
    clean_log.type = "auto"

    clean_log_repo.clear()
    assert len(clean_log_repo.list_by_did(did)) == 0
    assert clean_log_repo.list_by_id(clean_log.clean_log_id) is None

    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 1
    assert clean_log_repo.list_by_id(clean_log.clean_log_id) is not None

    rid = "sdu8"
    clean_log.clean_log_id = f"{did}@{start}@{rid}"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2

    clean_log.ts = 1699297517 + 1
    clean_log.clean_log_id = f"{did}@{clean_log.ts}@{rid}"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 3

    rid = "sdu7"
    clean_log.clean_log_id = f"{did}@{start}@{rid}"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 4

    did = "cßa9sbas"
    clean_log.clean_log_id = f"{did}@{clean_log.ts}@{rid}"
    clean_log.did = did
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 1

    clean_log.type = "area"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2

    clean_log_repo.clear()
    assert clean_log_repo.list_by_id(clean_log.clean_log_id) is None

    clean_log.type = "a"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 1

    clean_log.type = "b"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2

    clean_log.type = "b"
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2

    clean_log.last = 1699297520
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2

    clean_log.area = 28
    clean_log_repo.add_or_update(clean_log)
    assert len(clean_log_repo.list_by_did(did)) == 2


@pytest.mark.usefixtures("clean_database")
def test_clean_logs_remove_by_id() -> None:
    did = "test-device"
    cid = "test-clean"
    ts = 1699297517

    # Add multiple entries
    log1 = CleanLog(f"{did}@{ts}@r1")
    log1.did = did
    log1.cid = cid
    log1.ts = ts
    log1.type = "auto"

    log2 = CleanLog(f"{did}@{ts}@r2")
    log2.did = did
    log2.cid = cid
    log2.ts = ts
    log2.type = "auto"

    clean_log_repo.clear()
    clean_log_repo.add_or_update(log1)
    clean_log_repo.add_or_update(log2)

    # Confirm both are added
    logs = clean_log_repo.list_by_did(did)
    assert len(logs) == 2

    # Remove one by ID
    clean_log_repo.remove_by_id(log1.clean_log_id)

    # Confirm only one remains, and it's not log1
    logs = clean_log_repo.list_by_did(did)
    assert len(logs) == 1
    assert logs[0].clean_log_id == log2.clean_log_id
