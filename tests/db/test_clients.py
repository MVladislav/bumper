import pytest

from bumper.db import client_repo, user_repo


@pytest.mark.usefixtures("clean_database")
def test_client_db() -> None:
    client_repo.add("bumper", "user_123", "realm_123", "resource_123")
    assert client_repo.get("user_123")  # Test client was added

    client_repo.set_mqtt("user_123", True)
    assert client_repo.get("user_123").mqtt_connection  # Test that mqtt was set True for client

    client_repo.set_xmpp("user_123", False)
    assert client_repo.get("user_123").xmpp_connection is False  # Test that xmpp was set False for client

    disconnected = 0
    for _ in client_repo.list_all():
        disconnected = disconnected + 1
    assert disconnected > 0  # Test len of connected xmpp clients is 1

    client_repo.reset_all_connections()
    assert client_repo.get("user_123").mqtt_connection is False  # Test that mqtt was reset False for client
    assert client_repo.get("user_123").xmpp_connection is False  # Test that xmpp was reset False for client

    client_repo.remove("user_123")
    assert client_repo.get("user_123") is None


@pytest.mark.usefixtures("clean_database")
def test_client_add_no_existing() -> None:
    # Add a new client
    client_repo.add("bumper", "user_456", "realm_456", "resource_456")

    # Verify that the new client was added successfully
    assert client_repo.get("user_456") is not None


@pytest.mark.usefixtures("clean_database")
def test_client_add_existing() -> None:
    # Add an initial client
    client_repo.add("bumper", "user_789", "realm_789", "resource_789")

    # Try to add a new client with the same resource
    client_repo.add("bumper", "user_789", "realm_789", "resource_789")

    # Verify that the existing client is not overwritten
    client = client_repo.get("user_789")
    assert client is not None
    assert client.resource == "resource_789"


@pytest.mark.usefixtures("clean_database")
def test_client_remove() -> None:
    # Add a client
    client_repo.add("bumper", "user_remove", "realm_remove", "resource_remove")

    # Remove the added client
    client_repo.remove("user_remove")

    # Verify that the client was removed
    assert client_repo.get("user_remove") is None


@pytest.mark.usefixtures("clean_database")
def test_client_set_status() -> None:
    # Add a client
    client_repo.add("bumper", "user_status", "realm_status", "resource_status")

    # Set MQTT and XMPP status for the client
    client_repo.set_mqtt("user_status", True)
    client_repo.set_xmpp("user_status", True)

    # Verify that the status was set correctly
    client = client_repo.get("user_status")
    assert client is not None
    assert client.mqtt_connection is True
    assert client.xmpp_connection is True


@pytest.mark.usefixtures("clean_database")
def test_client_reset_connection_status() -> None:
    # Add multiple clients
    client_repo.add("bumper", "user_reset_1", "realm_reset_1", "resource_reset_1")
    client_repo.add("bumper", "user_reset_2", "realm_reset_2", "resource_reset_2")

    # Set MQTT and XMPP status for the clients
    client_repo.set_mqtt("user_reset_1", True)
    client_repo.set_xmpp("user_reset_2", True)

    # Reset connection status for all clients
    client_repo.reset_all_connections()

    # Verify that connection status was reset for all clients
    client_1 = client_repo.get("user_reset_1")
    client_2 = client_repo.get("user_reset_2")
    assert client_1.mqtt_connection is False
    assert client_2.xmpp_connection is False


@pytest.mark.usefixtures("clean_database")
def test_client_alias_merges_duplicate_records() -> None:
    """Names one account connected with become one client record."""
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")
    client_repo.add("app", "legacy", "realm", "resource")
    client_repo.set_mqtt("legacy", True)

    client_repo.add("app", "canonical", "realm", "resource")

    client = client_repo.get("canonical")
    assert client is not None
    assert client.userid == "canonical"
    assert client.mqtt_connection is True
    assert len(client_repo.list_all()) == 1
    assert client_repo.get("legacy").userid == "canonical"

    client_repo.set_xmpp("legacy", True)
    assert client_repo.get("canonical").xmpp_connection is True


@pytest.mark.usefixtures("clean_database")
def test_client_reassign_user_merges_onto_target() -> None:
    """Moving a client to another account keeps one record per account."""
    client_repo.add("app", "legacy", "realm", "resource")
    client_repo.set_xmpp("legacy", True)
    client_repo.add("app", "canonical", "realm", "resource")

    client_repo.reassign_user("legacy", "canonical")

    assert len(client_repo.list_all()) == 1
    client = client_repo.get("canonical")
    assert client is not None
    assert client.xmpp_connection is True


@pytest.mark.usefixtures("clean_database")
def test_client_add_resolves_an_account_alias() -> None:
    """A transport that still presents an older name is stored on the account."""
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")

    client_repo.add("app", "legacy", "realm", "resource")

    assert len(client_repo.list_all()) == 1
    client = client_repo.get("legacy")
    assert client is not None
    assert client.userid == "canonical"


@pytest.mark.usefixtures("clean_database")
def test_client_reconcile_drops_orphans_and_moves_aliases() -> None:
    """Startup keeps one client for every account and drops stale names."""
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")
    client_repo.add("app", "canonical", "realm", "resource")
    client_repo.add("app", "legacy", "realm", "resource")
    client_repo.add("app", "orphan", "realm", "resource")

    client_repo.reconcile(user_repo.list_all())

    assert len(client_repo.list_all()) == 1
    assert client_repo.get("orphan") is None
    client = client_repo.get("canonical")
    assert client is not None


@pytest.mark.usefixtures("clean_database")
def test_client_get_all() -> None:
    # Add multiple clients
    client_repo.add("bumper", "user_all_1", "realm_all_1", "resource_all_1")
    client_repo.add("bumper", "user_all_2", "realm_all_2", "resource_all_2")

    # Get all clients
    all_clients = client_repo.list_all()

    # Verify that all clients were retrieved
    assert len(all_clients) == 2

    # Verify that each client has the expected resource
    resources = {client.resource for client in all_clients}
    assert "resource_all_1" in resources
    assert "resource_all_2" in resources


@pytest.mark.usefixtures("clean_database")
def test_client_lookup_by_an_unknown_client_id_does_not_fall_back() -> None:
    """A client id names one row, never the first row of the account."""
    user_repo.add("user")
    client_repo.add("first", "user", "realm", "resource_one", client_id="client_one")
    client_repo.add("second", "user", "realm", "resource_two", client_id="client_two")

    assert client_repo.get("user", client_id="missing") is None

    client_repo.remove("user", client_id="missing")
    assert len(client_repo.list_all()) == 2


@pytest.mark.usefixtures("clean_database")
def test_client_remove_one_resource_keeps_the_other() -> None:
    """Removing one client of an account leaves the other clients alone."""
    user_repo.add("user")
    client_repo.add("first", "user", "realm", "resource_one", client_id="client_one")
    client_repo.add("second", "user", "realm", "resource_two", client_id="client_two")

    client_repo.remove("user", resource="resource_one")

    assert client_repo.get("user", client_id="client_one") is None
    assert client_repo.get("user", client_id="client_two") is not None
    assert len(client_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database")
def test_client_remove_by_device_id_keeps_other_clients() -> None:
    """A device id can select its client when no resource is available."""
    user_repo.add("user")
    client_repo.add("first", "user", "realm", "resource_one", device_id="device_one")
    client_repo.add("second", "user", "realm", "resource_two", device_id="device_two")

    client_repo.remove("user", device_id="device_one")

    assert client_repo.get("user", resource="resource_one") is None
    assert client_repo.get("user", resource="resource_two") is not None
