import pytest

from bumper.db import clean_log_repo as clr, db
from bumper.db.migration import _migrate_clean_logs_0_2_2_to_0_2_3
from bumper.utils.errors import MigrationError


@pytest.mark.usefixtures("clean_database")
def test_migrate_clean_logs_flattens_nested_list() -> None:
    # Insert old-style nested logs
    clr.table.insert(
        {
            "did": "device1",
            "logs": [
                {"clean_log_id": "device1@1", "type": "auto", "ts": 123},
                {"clean_log_id": "device1@2", "type": "auto", "ts": 123},
            ],
        },
    )
    _migrate_clean_logs_0_2_2_to_0_2_3(db.get_db())

    # Verify table is flattened
    all_docs = clr.list_by_did("device1")
    assert len(all_docs) == 2
    for doc in all_docs:
        assert doc.did == "device1"
        assert doc.type == "auto"
        assert doc.ts == 123


@pytest.mark.usefixtures("clean_database")
def test_migrate_clean_logs_raises_if_logs_not_list() -> None:
    clr.table.insert({"did": "device1", "logs": "not_a_list"})
    with pytest.raises(MigrationError, match="Invalid clean_logs schema"):
        _migrate_clean_logs_0_2_2_to_0_2_3(db.get_db())


@pytest.mark.usefixtures("clean_database")
def test_migrate_clean_logs_raises_if_log_entry_not_dict() -> None:
    clr.table.insert({"did": "device1", "logs": ["not_a_dict"]})
    with pytest.raises(MigrationError, match="Invalid clean_logs entry"):
        _migrate_clean_logs_0_2_2_to_0_2_3(db.get_db())
