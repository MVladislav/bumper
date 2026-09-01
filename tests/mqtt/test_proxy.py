"""Tests for bumper/mqtt/proxy.py."""

from unittest import mock

from amqtt.client import ClientConfig, MQTTClient
from amqtt.session import IncomingApplicationMessage

from bumper.mqtt import proxy as mqtt_proxy
from bumper.utils.settings import config as bumper_isc


def _fake_client() -> mock.AsyncMock:
    """Return an AsyncMock modelling an MQTTClient."""
    client = mock.AsyncMock()
    client.session.transitions.is_connected = mock.Mock(side_effect=[True, True, False])
    client.deliver_message.side_effect = [
        IncomingApplicationMessage(None, "iot/atr/test/from_did/from_class/from_res/j", 0, b"payload", False),
        IncomingApplicationMessage(
            None,
            "iot/p2p/test/from_did/from_class/from_res/to_did/to_class/to_res/q/req123",
            0,
            b"cmd",
            False,
        ),
    ]
    return client


def test_proxy_client_uses_stock_mqttclient() -> None:
    """The proxy uses amqtt's stock MQTTClient, not a local cert-verification subclass."""
    proxy = mqtt_proxy.ProxyClient("client_1", "127.0.0.1", port=8883)
    assert isinstance(proxy._client, MQTTClient)
    assert proxy._client.config.check_hostname is False
    assert proxy._client.config.verify_cert is False


def test_proxy_client_accepts_explicit_config() -> None:
    """An explicit config is honored and not overridden by the default."""
    proxy = mqtt_proxy.ProxyClient(
        "client_1",
        "127.0.0.1",
        port=8883,
        config=ClientConfig(check_hostname=False, verify_cert=False),
    )
    assert proxy._client.config.verify_cert is False


async def test_proxy_disconnect_suppresses_attribute_error() -> None:
    """disconnect() must not raise if the underlying client has no session."""
    proxy = mqtt_proxy.ProxyClient("client_1", "127.0.0.1", port=8883)
    proxy._client.disconnect = mock.AsyncMock(side_effect=AttributeError("no session"))
    # Should not raise
    await proxy.disconnect()
    proxy._client.disconnect.assert_awaited_once()


async def test_handle_messages_forwards_and_rewrites_p2p_topic() -> None:
    """_handle_messages forwards messages to the helperbot and rewrites p2p sender topics."""
    proxy = mqtt_proxy.ProxyClient("client_1", "127.0.0.1", port=8883)
    proxy._client = _fake_client()

    helperbot = mock.AsyncMock()
    bumper_isc.mqtt_helperbot = helperbot

    await proxy._handle_messages()

    # First message (atr broadcast): forwarded unchanged
    helperbot.publish.assert_has_calls(
        [
            mock.call("iot/atr/test/from_did/from_class/from_res/j", "payload"),
            # Second message (p2p): sender topic segment rewritten to 'proxyhelper'
            mock.call(
                "iot/p2p/test/proxyhelper/from_class/from_res/to_did/to_class/to_res/q/req123",
                "cmd",
            ),
        ],
    )

    # The p2p topic keeps a mapping from request id -> original sender did
    assert proxy.request_mapper["req123"] == "from_did"


async def test_handle_messages_returns_without_session() -> None:
    """_handle_messages returns immediately when the client has no session."""
    proxy = mqtt_proxy.ProxyClient("client_1", "127.0.0.1", port=8883)
    proxy._client.session = None
    bumper_isc.mqtt_helperbot = mock.AsyncMock()
    await proxy._handle_messages()  # should not raise


async def test_proxy_connect_uri() -> None:
    """The proxy builds a TLS URI with credentials for the configured port."""
    proxy = mqtt_proxy.ProxyClient("client_1", "broker.example", port=8883)
    proxy._client.connect = mock.AsyncMock()
    await proxy.connect("user", "pass")
    proxy._client.connect.assert_awaited_once_with("mqtts://user:pass@broker.example:8883")
