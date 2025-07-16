import pytest
from tinydb.table import Document

from bumper.db import db, helpers


@pytest.mark.asyncio
async def test_db_get() -> None:
    # Call the _db_get function
    with db.get_db() as result:
        # Verify that TinyDB was instantiated with the correct file path
        # assert result == bumper_isc.db_file

        result.drop_tables()

        result.table(db.TABLE_USERS).insert({})
        result.table(db.TABLE_CLIENTS).insert({})
        result.table(db.TABLE_BOTS).insert({})
        result.table(db.TABLE_TOKENS).insert({})
        result.table(db.TABLE_CLEAN_LOGS).insert({})

        # Verify that tables were created
        assert db.TABLE_USERS in result.tables()
        assert db.TABLE_CLIENTS in result.tables()
        assert db.TABLE_BOTS in result.tables()
        assert db.TABLE_TOKENS in result.tables()
        assert db.TABLE_CLEAN_LOGS in result.tables()

        result.drop_tables()

        assert len(result) == 0


def test_logging_message_not_document(caplog: pytest.LogCaptureFixture) -> None:
    value_name = "test_value"

    with caplog.at_level("DEBUG"):
        # Case 1: None value
        value = None
        helpers.warn_if_not_doc(value, value_name)
        assert f"'{value_name}' is not a TinyDB Document: '<class 'NoneType'>'" in caplog.text
        caplog.clear()

        # Case 2: Single Document (should not log)
        value = Document({"key": "value"}, 0)
        helpers.warn_if_not_doc(value, value_name)
        assert not caplog.text
        caplog.clear()

        # Case 3: List of Documents
        value = [Document({"key": "value"}, 0), Document({"key": "value"}, 0)]
        helpers.warn_if_not_doc(value, value_name)
        assert f"'{value_name}' is not a TinyDB Document: '<class 'list'>'" in caplog.text
        caplog.clear()

        # Case 4: Other types
        value = "some_string"
        helpers.warn_if_not_doc(value, value_name)
        assert f"'{value_name}' is not a TinyDB Document: '<class 'str'>'" in caplog.text
