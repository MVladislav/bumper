from datetime import datetime, timedelta
from pathlib import Path

import jwt
import pytest
from tinydb import TinyDB

from bumper.db import bot_repo, client_repo, identity, token_repo, user_repo
from bumper.db.db import query_instance
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import generate_jwt_helper
from bumper.web.utils.models import BumperUser


@pytest.mark.usefixtures("clean_database")
def test_user_db(test_files: dict[str, Path()]) -> None:
    user_repo.add("new_testuser")
    assert user_repo.get_by_id("new_testuser").userid == "new_testuser"

    # Test user_add when user already exists
    user_repo.add("new_testuser")
    assert user_repo.get_by_id("new_testuser").userid == "new_testuser"  # User should still exist, not added again

    user_repo.add("testuser")  # Add testuser

    assert user_repo.get_by_id("testuser").userid == "testuser"  # Test that testuser was created and returned

    user_repo.add_device("testuser", "dev_1234")  # Add device to testuser

    assert user_repo.get_by_device_id("dev_1234").userid == "testuser"  # Test that testuser was found by deviceid

    user_repo.set_device_name("testuser", "dev_1234", "Test Phone")
    assert user_repo.get_by_id("testuser").device_names == {"dev_1234": "Test Phone"}

    user_repo.set_device_verification("testuser", "ENABLED")
    assert user_repo.get_by_id("testuser").device_verification == "ENABLED"

    user_repo.set_email("testuser", "user@example.com")
    assert user_repo.get_by_id("testuser").email == "user@example.com"

    user_repo.set_backup_email("testuser", "backup@example.com")
    assert user_repo.get_by_id("testuser").backup_email == "backup@example.com"

    user_repo.remove_device("testuser", "dev_1234")  # Remove device from testuser

    assert "dev_1234" not in user_repo.get_by_id("testuser").devices
    assert "dev_1234" not in user_repo.get_by_id("testuser").device_names
    # Test that dev_1234 was not found in testuser devices

    user_repo.add_bot("testuser", "bot_1234")  # Add bot did to testuser

    assert "bot_1234" in user_repo.get_by_id("testuser").bots
    # Test that bot was found in testuser's bot list

    user_repo.remove_bot("testuser", "bot_1234")  # Remove bot did from testuser

    assert "bot_1234" not in user_repo.get_by_id("testuser").bots
    # Test that bot was not found in testuser's bot list

    token_repo.add("testuser", "token_1234")  # Add token to testuser

    assert token_repo.verify("testuser", "token_1234")
    # Test that token was found for testuser

    assert token_repo.get("testuser", "token_1234")
    assert token_repo.get_first("testuser")
    # Test that token was returned for testuser

    token_repo.add_auth_code("testuser", "auth_1234")  # Add authcode to token_1234 for testuser
    assert token_repo.verify_auth_code("testuser", "auth_1234")
    # Test that authcode was found for testuser

    token_repo.revoke_token("testuser", "token_1234")  # Remove authcode from testuser
    assert token_repo.verify_auth_code("testuser", "auth_1234") is False
    # Test that authcode was not found for testuser
    token_repo.revoke_token("testuser", "token_1234")  # Remove token from testuser
    assert token_repo.verify("testuser", "token_1234") is False  # Test that token was not found for testuser
    token_repo.add("testuser", "token_1234")  # Add token_1234
    token_repo.add("testuser", "token_4321")  # Add token_4321
    assert len(token_repo.list_for_user("testuser")) == 2  # Test 2 tokens are available
    assert token_repo.get_first("testuser")
    token_repo.revoke_all_for_user("testuser")  # Revoke all tokens
    assert len(token_repo.list_for_user("testuser")) == 0  # Test 0 tokens are available
    assert token_repo.get_first("testuser") is None

    # Test _user_full_upsert
    new_user = BumperUser(userid="new_testuser")
    user_repo._upsert(new_user.as_dict(), query_instance.userid == new_user.userid)
    assert user_repo.get_by_id("new_testuser").userid == "new_testuser"

    db_test = TinyDB(str(test_files["db"]))
    tokens = db_test.table("tokens")
    tokens.insert(
        {
            "userid": "testuser",
            "token": "token_123456",
            "expiration": f"{datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=-10)}",
        },
    )  # Add expired token
    db_test.close()
    assert len(token_repo.list_for_user("testuser")) == 1  # Test 1 tokens are available
    assert token_repo.get_first("testuser")
    token_repo.revoke_user_expired("testuser")  # Revoke expired tokens
    assert len(token_repo.list_for_user("testuser")) == 0  # Test 0 tokens are available
    assert token_repo.get_first("testuser") is None

    db_test = TinyDB(str(test_files["db"]))
    tokens = db_test.table("tokens")
    tokens.insert(
        {
            "userid": "testuser",
            "token": "token_1234",
            "expiration": f"{datetime.now(tz=bumper_isc.LOCAL_TIMEZONE) + timedelta(seconds=-10)}",
        },
    )  # Add expired token
    db_test.close()
    assert len(token_repo.list_for_user("testuser")) == 1  # Test 1 tokens are available
    assert token_repo.get_first("testuser")
    token_repo.revoke_expired()  # Revoke expired tokens
    assert len(token_repo.list_for_user("testuser")) == 0  # Test 0 tokens are available
    assert token_repo.get_first("testuser") is None

    # Test login_by_it_token
    token_repo.add("testuser", "token_1234")
    token_repo.add_it_token("testuser", "auth_1234")
    login_result = token_repo.login_by_it_token("auth_1234")
    assert login_result.as_dict() == {"token": "token_1234", "userid": "testuser"}


@pytest.mark.usefixtures("clean_database")
def test_user_repo_extras() -> None:
    user_id = "testuser_extra"
    home_id = "home123"

    # Add user
    user_repo.add(user_id)
    assert user_repo.get_by_id(user_id) is not None

    # Add home_id manually to ensure get_by_home_id can match it
    user_repo.add_home_id(user_id, home_id)
    user = user_repo.get_by_id(user_id)
    assert user
    assert home_id in user.homeids

    # Test get_by_home_id
    user_by_home = user_repo.get_by_home_id(home_id)
    assert user_by_home is not None
    assert user_by_home.userid == user_id

    # Test list_all
    all_users = user_repo.list_all()
    assert isinstance(all_users, list)
    assert any(u.userid == user_id for u in all_users)

    # Test remove_home_id
    user_repo.remove_home_id(user_id, home_id)
    user = user_repo.get_by_id(user_id)
    assert home_id not in user.homeids

    # Test remove
    user_repo.remove(user_id)
    assert user_repo.get_by_id(user_id) is None


@pytest.mark.usefixtures("clean_database")
def test_user_alias_updates_canonical_record() -> None:
    """A name the account used earlier updates the one user record."""
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")

    assert user_repo.get_by_id("legacy").userid == "canonical"

    user_repo.set_email("legacy", "user@example.com")
    assert user_repo.get_by_id("canonical").email == "user@example.com"


@pytest.mark.usefixtures("clean_database")
def test_duplicate_user_merges_into_older_record() -> None:
    """A second record for the same account moves its data to the older one."""
    user_repo.add("canonical")
    user_repo.add_device("canonical", "device")
    user_repo.add_bot("canonical", "bot-a")

    user_repo.add("legacy")
    user_repo.add_device("legacy", "device")
    user_repo.add_bot("legacy", "bot-b")
    user_repo.set_email("legacy", "legacy@example.com")
    token_repo.add("legacy", "legacy-token")

    canonical = user_repo.get_by_id("canonical")
    assert canonical is not None
    merged = identity.adopt_alias(canonical, "legacy")

    assert merged.userid == "canonical"
    assert len(user_repo.list_all()) == 1
    assert user_repo.get_by_id("legacy").userid == "canonical"
    assert "bot-b" in merged.bots
    assert merged.email == "legacy@example.com"
    assert len(token_repo.list_for_user("canonical")) == 1
    assert token_repo.list_for_user("legacy") == []


@pytest.mark.usefixtures("clean_database")
def test_bind_device_moves_ownership() -> None:
    """A device belongs to the account that logged in last."""
    user_repo.add("first")
    user_repo.add("second")
    user_repo.add_device("first", "device")
    user_repo.add_device("second", "device")

    user_repo.bind_device("second", "device")

    assert user_repo.get_by_device_id("device").userid == "second"
    assert "device" not in user_repo.get_by_id("first").devices
    assert "device" in user_repo.get_by_id("second").devices


@pytest.mark.usefixtures("clean_database")
def test_reconcile_users_merges_records_that_share_a_device() -> None:
    """Startup keeps one account for an app installation and moves its data."""
    user_repo.add("canonical")
    user_repo.add_device("canonical", "device")
    user_repo.add("legacy")
    user_repo.add_device("legacy", "device")
    token_repo.add("legacy", "legacy-token")
    client_repo.add("app", "legacy", "realm", "resource")

    identity.reconcile_users()

    assert len(user_repo.list_all()) == 1
    assert user_repo.get_by_id("legacy").userid == "canonical"
    assert token_repo.list_for_user("legacy") == []
    assert len(token_repo.list_for_user("canonical")) == 1
    client = client_repo.get("legacy")
    assert client is not None
    assert client.userid == "canonical"


@pytest.mark.usefixtures("clean_database")
def test_reconcile_users_keeps_records_with_different_devices() -> None:
    """A device belongs to one account, and another device does not merge."""
    user_repo.add("first")
    user_repo.add_device("first", "device-a")
    user_repo.add("second")
    user_repo.add_device("second", "device-b")

    identity.reconcile_users()

    assert len(user_repo.list_all()) == 2


@pytest.mark.usefixtures("clean_database")
async def test_transport_secret_accepts_a_verified_jwt_for_an_alias() -> None:
    """A token that names an alias authenticates the account it points at."""
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")
    token, _ = await generate_jwt_helper(data={"u": "legacy"}, t="a")

    assert identity.verify_transport_secret("canonical", token)
    assert not identity.verify_transport_secret("other", token)
    assert identity.resolve_transport_user("legacy", token).userid == "canonical"


@pytest.mark.usefixtures("clean_database")
async def test_transport_name_is_not_adopted_from_an_unverified_jwt() -> None:
    """An unsigned claim cannot move an account, even when USE_AUTH is off."""
    user_repo.add("canonical")
    user_repo.add("target")
    forged = jwt.encode(
        {
            "u": "target",
            "t": "a",
            "exp": int(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp()) + 60,
        },
        "not-the-server-key",
        algorithm="HS256",
    )

    account = identity.resolve_transport_user("canonical", forged)

    assert account is not None
    assert account.userid == "canonical"
    assert len(user_repo.list_all()) == 2
    assert user_repo.get_by_id("target").userid == "target"


@pytest.mark.usefixtures("clean_database")
async def test_transport_secret_rejects_a_jwt_bumper_did_not_sign() -> None:
    """A token signed by another key is not an access token."""
    user_repo.add("canonical")
    token = jwt.encode(
        {
            "u": "canonical",
            "t": "a",
            "exp": int(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp()) + 60,
        },
        "not-the-server-key",
        algorithm="HS256",
    )

    assert not identity.verify_transport_secret("canonical", token)


@pytest.mark.usefixtures("clean_database")
async def test_transport_secret_rejects_an_expired_jwt() -> None:
    """An expired access token is not accepted."""
    user_repo.add("canonical")
    token, _ = await generate_jwt_helper(data={"u": "canonical"}, t="a", exp_seconds=-1)

    assert not identity.verify_transport_secret("canonical", token)


@pytest.mark.usefixtures("clean_database")
async def test_transport_secret_rejects_a_refresh_token() -> None:
    """A refresh token cannot stand in for an access token."""
    user_repo.add("canonical")
    token, _ = await generate_jwt_helper(data={"u": "canonical"}, t="r")

    assert not identity.verify_transport_secret("canonical", token)


@pytest.mark.usefixtures("clean_database")
def test_transport_secret_accepts_every_secret_bumper_issued() -> None:
    """The portal token, the auth code, and the IT token all authenticate."""
    user_repo.add("canonical")
    token_repo.add("canonical", "portal-token")
    token_repo.add_auth_code("canonical", "auth-code")
    token_repo.add_it_token("canonical", "it-token")

    assert identity.verify_transport_secret("canonical", "portal-token")
    assert identity.verify_transport_secret("canonical", "auth-code")
    assert identity.verify_transport_secret("canonical", "it-token")
    assert not identity.verify_transport_secret("other", "portal-token")


@pytest.mark.usefixtures("clean_database")
def test_reconcile_users_merges_records_that_share_a_public_id() -> None:
    """The account id names one account even when two records carry it."""
    user_repo.add("first")
    first = user_repo.get_by_id("first")
    assert first is not None
    first.account_uid = "20240101000000_" + "a" * 32
    user_repo.set_identity(first)

    user_repo.add("second")
    second = user_repo.get_by_id("second")
    assert second is not None
    second.account_uid = first.account_uid
    user_repo.set_identity(second)

    identity.reconcile_users()

    assert len(user_repo.list_all()) == 1
    assert user_repo.get_by_id("second") is not None
    assert user_repo.get_by_id("second").userid == "first"


@pytest.mark.usefixtures("clean_database")
def test_create_account_is_idempotent() -> None:
    """Asking for the same login name twice returns the same account."""
    first = identity.create_account("same-login")
    second = identity.create_account("same-login")

    assert first.userid == second.userid
    assert len(user_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database")
def test_reconcile_bot_owners_shares_all_bots_with_every_user() -> None:
    """Startup gives all known robots to every local account."""
    user_repo.add("ha_user")
    user_repo.add("app_user")
    user_repo.add("another_user")
    bot_repo.add("sn_one", "did_one", "class_one", "resource_one", "eco-ng")
    bot_repo.add("sn_two", "did_two", "class_two", "resource_two", "eco-ng")

    identity.reconcile_bot_owners()

    assert all(set(user.bots) == {"did_one", "did_two"} for user in user_repo.list_all())


@pytest.mark.usefixtures("clean_database")
def test_new_user_receives_bots_already_known_to_the_service() -> None:
    """An account created after robot discovery gets the shared inventory."""
    bot_repo.add("sn_one", "did_one", "class_one", "resource_one", "eco-ng")
    bot_repo.add("sn_two", "did_two", "class_two", "resource_two", "eco-ng")

    user = identity.create_account("late_user")

    assert set(user_repo.get_by_id(user.userid).bots) == {"did_one", "did_two"}


@pytest.mark.usefixtures("clean_database")
def test_runtime_bot_assignment_reaches_every_user() -> None:
    """A newly registered robot is assigned across existing accounts."""
    user_repo.add("ha_user")
    user_repo.add("app_user")

    identity.assign_bot_to_all_users("did_new")

    assert all("did_new" in user.bots for user in user_repo.list_all())
