from datetime import datetime, timedelta

import pytest
from tinydb import TinyDB

from bumper.utils import db
from bumper.utils.settings import config as bumper_isc
from bumper.web.models import BumperUser


@pytest.mark.usefixtures("clean_database")
def test_user_db() -> None:
    db.user_add("new_testuser")
    assert db.user_by_user_id("new_testuser").userid == "new_testuser"

    # Test user_add when user already exists
    db.user_add("new_testuser")
    assert db.user_by_user_id("new_testuser").userid == "new_testuser"  # User should still exist, not added again

    db.user_add("testuser")  # Add testuser

    assert db.user_by_user_id("testuser").userid == "testuser"  # Test that testuser was created and returned

    db.user_add_device("testuser", "dev_1234")  # Add device to testuser

    assert db.user_by_device_id("dev_1234").userid == "testuser"  # Test that testuser was found by deviceid

    db.user_remove_device("testuser", "dev_1234")  # Remove device from testuser

    assert "dev_1234" not in db.user_by_user_id("testuser").devices
    # Test that dev_1234 was not found in testuser devices

    db.user_add_bot("testuser", "bot_1234")  # Add bot did to testuser

    assert "bot_1234" in db.user_by_user_id("testuser").bots
    # Test that bot was found in testuser's bot list

    db.user_remove_bot("testuser", "bot_1234")  # Remove bot did from testuser

    assert "bot_1234" not in db.user_by_user_id("testuser").bots
    # Test that bot was not found in testuser's bot list

    db.user_add_token("testuser", "token_1234")  # Add token to testuser

    assert db.check_token("testuser", "token_1234")
    # Test that token was found for testuser

    assert db.user_get_token("testuser", "token_1234")
    assert db.user_get_token_v2("testuser")
    # Test that token was returned for testuser

    db.user_add_auth_code("testuser", "token_1234", "auth_1234")  # Add authcode to token_1234 for testuser
    assert db.check_auth_code("testuser", "auth_1234")
    # Test that authcode was found for testuser

    db.user_revoke_auth_code("testuser", "token_1234")  # Remove authcode from testuser
    assert db.check_auth_code("testuser", "auth_1234") is False
    # Test that authcode was not found for testuser
    db.user_revoke_token("testuser", "token_1234")  # Remove token from testuser
    assert db.check_token("testuser", "token_1234") is False  # Test that token was not found for testuser
    db.user_add_token("testuser", "token_1234")  # Add token_1234
    db.user_add_token("testuser", "token_4321")  # Add token_4321
    assert len(db.user_get_tokens("testuser")) == 2  # Test 2 tokens are available
    assert db.user_get_token_v2("testuser")
    db.user_revoke_all_tokens("testuser")  # Revoke all tokens
    assert len(db.user_get_tokens("testuser")) == 0  # Test 0 tokens are available
    assert db.user_get_token_v2("testuser") is None

    # Test _user_full_upsert
    new_user = BumperUser(userid="new_testuser")
    db._user_full_upsert(new_user)
    assert db.user_by_user_id("new_testuser").userid == "new_testuser"

    db_test = TinyDB("tests/_test_files/tmp.db")
    tokens = db_test.table("tokens")
    tokens.insert(
        {
            "userid": "testuser",
            "token": "token_123456",
            "expiration": f"{datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=-10)}",
        },
    )  # Add expired token
    db_test.close()
    assert len(db.user_get_tokens("testuser")) == 1  # Test 1 tokens are available
    assert db.user_get_token_v2("testuser")
    db.user_revoke_expired_tokens("testuser")  # Revoke expired tokens
    assert len(db.user_get_tokens("testuser")) == 0  # Test 0 tokens are available
    assert db.user_get_token_v2("testuser") is None

    db_test = TinyDB("tests/_test_files/tmp.db")
    tokens = db_test.table("tokens")
    tokens.insert(
        {
            "userid": "testuser",
            "token": "token_1234",
            "expiration": f"{datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=-10)}",
        },
    )  # Add expired token
    db_test.close()
    assert len(db.user_get_tokens("testuser")) == 1  # Test 1 tokens are available
    assert db.user_get_token_v2("testuser")
    db.revoke_expired_tokens()  # Revoke expired tokens
    assert len(db.user_get_tokens("testuser")) == 0  # Test 0 tokens are available
    assert db.user_get_token_v2("testuser") is None

    # Test login_by_it_token
    db.user_add_token("testuser", "token_1234")
    db.user_add_auth_code("testuser", "token_1234", "auth_1234")
    login_result = db.login_by_it_token("auth_1234")
    assert login_result == {"token": "token_1234", "userid": "testuser"}

    # Test token_by_auth_code
    auth_token = db.token_by_auth_code("auth_1234")
    assert auth_token is not None
    assert auth_token["token"] == "token_1234"  # noqa: S105

    # Test user_add_auth_code_v2
    db.user_add_auth_code_v2("testuser", "auth_5678")
    assert db.check_auth_code("testuser", "auth_5678")
