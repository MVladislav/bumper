import pytest

from bumper.db import bot_repo


@pytest.mark.usefixtures("clean_database")
def test_bot_db() -> None:
    bot_repo.add("sn_123", "did_123", "dev_123", "res_123", "co_123")
    assert bot_repo.get("did_123")  # Test that bot was added to db

    bot_repo.set_nick("did_123", "nick_123")
    assert bot_repo.get("did_123").nick == "nick_123"  # Test that nick was added to bot

    bot_repo.set_mqtt("did_123", True)
    assert bot_repo.get("did_123").mqtt_connection  # Test that mqtt was set True for bot

    bot_repo.set_xmpp("did_123", True)
    assert bot_repo.get("did_123").xmpp_connection  # Test that xmpp was set True for bot

    bot_repo.reset_all_connections()
    assert bot_repo.get("did_123").mqtt_connection is False  # Test that mqtt was reset False for bot
    assert bot_repo.get("did_123").xmpp_connection is False  # Test that xmpp was reset False for bot

    bot_repo.remove("did_123")
    assert bot_repo.get("did_123") is None  # Test that bot is no longer in db


@pytest.mark.usefixtures("clean_database")
def test_bot_list_all() -> None:
    bot_repo.add("sn_1", "did_1", "class_1", "res_1", "co_1")
    bot_repo.add("sn_2", "did_2", "class_2", "res_2", "co_2")

    bots = bot_repo.list_all()
    assert len(bots) == 2
    assert sorted(bot.did for bot in bots) == ["did_1", "did_2"]


@pytest.mark.usefixtures("clean_database")
def test_bot_set_fields_with_none_did(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        # Try setting fields with did=None
        bot_repo.set_nick(None, "some_nick")
        assert "Failed to updated field as did is not set for :: DID: None :: field: nick :: value: some_nick" in caplog.text
        caplog.clear()

        bot_repo.set_mqtt(None, True)
        assert (
            "Failed to updated field as did is not set for :: DID: None :: field: mqtt_connection :: value: True" in caplog.text
        )
        caplog.clear()

        bot_repo.set_xmpp(None, True)
        assert (
            "Failed to updated field as did is not set for :: DID: None :: field: xmpp_connection :: value: True" in caplog.text
        )
        caplog.clear()

        # Ensure nothing was added to the database
        assert bot_repo.list_all() == []
