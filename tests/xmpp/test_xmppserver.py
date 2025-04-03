import asyncio
from unittest import mock

import pytest
from testfixtures import LogCapture

from bumper.xmpp.xmpp import XMPPAsyncClient, XMPPServer


def return_send_data(data: bytes) -> bytes:
    return data


def mock_transport_extra_info() -> tuple[str, int]:
    return ("127.0.0.1", 5223)


@pytest.fixture(autouse=True)
def cleanup_clients():
    """Ensure all XMPPAsyncClient instances are cleaned up after each test."""
    yield
    for client in XMPPServer.clients:
        client.cleanup()
    XMPPServer.clients.clear()


async def test_xmpp_server() -> None:
    xmpp_server = XMPPServer("127.0.0.1", 5223)
    await xmpp_server.start_async_server()

    with LogCapture("xmppserver") as _:
        _, writer = await asyncio.open_connection("127.0.0.1", 5223)

        writer.write(b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' />")  # Start stream
        await writer.drain()

        await asyncio.sleep(0.1)

        assert len(xmpp_server.clients) == 1  # Client count increased
        assert xmpp_server.clients[0].address[1] == writer.transport.get_extra_info("sockname")[1]

        writer.close()  # Close connection
        await writer.wait_closed()

        await asyncio.sleep(0.1)

        assert len(xmpp_server.clients) == 0  # Client count decreased

        _, writer = await asyncio.open_connection("127.0.0.1", 5223)

        writer.write(b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' />")  # Start stream
        await writer.drain()

        await asyncio.sleep(0.1)

    await xmpp_server.disconnect()


async def test_client_connect_no_starttls() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.CONNECT  # Set client state to CONNECT
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send connect stream from "client"
    test_data = (
        b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0' to='ecouser.net'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client available features
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"><required/></starttls>'
        '<mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl"><mechanism>PLAIN</mechanism></mechanisms></stream:features>'
    )

    # Reset mock calls
    mock_send.reset_mock()

    # Client sends auth - Ignoring the starttls, we don't force this with bumper
    test_data = (
        b'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">'
        b"AGZ1aWRfdG1wdXNlcgAwL0lPU0Y1M0QwN0JBL3VzXzg5ODgwMmZkYmM0NDQxYjBiYzgxNWIxZDFjNjgzMDJl</auth>"
    )
    xmppclient.parse_data(test_data)

    assert (
        mock_send.mock_calls[0][1][0] == '<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    )  # Client successfully authenticated
    assert xmppclient.state == xmppclient.INIT  # Client moved to INIT state


async def test_client_end_stream() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.CONNECT  # Set client state to CONNECT
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send end stream from "client"
    test_data = b"</stream:stream>"
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 1
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == "</stream:stream>"

    # Reset mock calls
    mock_send.reset_mock()

    # Send abnormal stream from "client"
    test_data = b"<badstr />"
    xmppclient.parse_data(test_data)

    # Reset mock calls
    mock_send.reset_mock()

    # Send blank from "client"
    test_data = b""
    xmppclient.parse_data(test_data)


async def test_client_connect_starttls_called() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.CONNECT  # Set client state to CONNECT
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send connect stream from "client"
    test_data = (
        b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0' to='ecouser.net'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client available features
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"><required/></starttls>'
        '<mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl"><mechanism>PLAIN</mechanism></mechanisms></stream:features>'
    )

    # Reset mock calls
    mock_send.reset_mock()

    mock_tls = xmppclient._handle_starttls = mock.Mock()

    # Send start tls from "client"
    test_data = b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>"
    xmppclient.parse_data(test_data)

    # After upgrading connection, server tells client to proceed with auth again
    assert mock_tls.called
    xmppclient.tls_upgraded = True

    # After TLS is upgraded, Client establishes session again and will auth this time
    # Send connect stream from "client"
    test_data = (
        b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0' to='ecouser.net'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client available features (without STARTTLS)
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl">'
        "<mechanism>PLAIN</mechanism></mechanisms></stream:features>"
    )
    # Reset mock calls
    mock_send.reset_mock()

    # Client sends auth
    test_data = (
        b'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">'
        b"AGZ1aWRfdG1wdXNlcgAwL0lPU0Y1M0QwN0JBL3VzXzg5ODgwMmZkYmM0NDQxYjBiYzgxNWIxZDFjNjgzMDJl</auth>"
    )
    xmppclient.parse_data(test_data)

    assert (
        mock_send.mock_calls[0][1][0] == '<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    )  # Client successfully authenticated
    assert xmppclient.state == xmppclient.INIT  # Client moved to INIT state


async def test_client_init() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.INIT  # Set client state to INIT
    xmppclient.uid = "fuid_tmpuser"
    xmppclient.clientresource = "IOSF53D07BA"
    xmppclient.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF53D07BA"
    xmppclient.type = xmppclient.CONTROLLER
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send connect stream from "client"
    test_data = (
        b"<stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0' to='ecouser.net'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client binds
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"/>'
        '<session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></stream:features>'
    )

    # Reset mock calls
    mock_send.reset_mock()

    # Send bind from "client"
    test_data = (
        b'<iq type="set" id="5E9872D5-547E-49AF-AE51-9EFAA282F952">'
        b'<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>IOSF53D07BA</resource></bind></iq>'
    )
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" id="5E9872D5-547E-49AF-AE51-9EFAA282F952">'
        '<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><jid>fuid_tmpuser@ecouser.net/IOSF53D07BA</jid></bind></iq>'
    )  # client successfully binded
    assert xmppclient.state == xmppclient.BIND  # client moved to BIND state

    # Reset mock calls
    mock_send.reset_mock()

    # Send set session from client
    test_data = (
        b'<iq type="set" id="FA1041E7-AA27-43DD-BAA3-64DE2DE56AA3"><session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></iq>'
    )
    xmppclient.parse_data(test_data)

    assert xmppclient.state == xmppclient.READY  # client moved to READY state
    assert mock_send.mock_calls[0][1][0] == '<iq type="result" id="FA1041E7-AA27-43DD-BAA3-64DE2DE56AA3" />'  # client ready

    # Reset mock calls
    mock_send.reset_mock()

    # Send presence from client
    test_data = b'<presence type="available"/>'
    xmppclient.parse_data(test_data)

    assert (
        mock_send.mock_calls[0][1][0] == '<presence to="fuid_tmpuser@ecouser.net/IOSF53D07BA"> dummy </presence>'
    )  # client presence - dummy response


async def test_bot_connect() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.CONNECT  # Set client state to CONNECT
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send connect stream from "bot"
    test_data = (
        b"<stream:stream xmlns:stream='http://etherx.jabber.org/streams'"
        b" xmlns='jabber:client' to='159.ecorobot.net' version='1.0'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client available features
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"><required/></starttls>'
        '<mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl"><mechanism>PLAIN</mechanism></mechanisms></stream:features>'
    )

    # Reset mock calls
    mock_send.reset_mock()

    # Send auth from "bot"
    test_data = (
        b"<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>"
        b"AEUwMDAwMDAwMDAwMDAwMDAxMjM0AGVuY3J5cHRlZF9wYXNz</auth>"
    )
    xmppclient.parse_data(test_data)

    assert (
        mock_send.mock_calls[0][1][0] == '<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    )  # Bot successfully authenticated
    assert xmppclient.state == xmppclient.INIT  # Bot moved to INIT state
    assert xmppclient.type == xmppclient.BOT  # Client type is now bot


async def test_bot_init() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.INIT  # Set client state to INIT
    xmppclient.uid = "E0000000000000001234"
    xmppclient.devclass = "159"
    xmppclient.type = xmppclient.BOT
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Send connect stream from "bot"
    test_data = (
        b"<stream:stream xmlns:stream='http://etherx.jabber.org/streams'"
        b" xmlns='jabber:client' to='159.ecorobot.net' version='1.0'>"
    )
    xmppclient.parse_data(test_data)

    # Expect 2 calls to send
    assert mock_send.call_count == 2
    # Server opens stream
    assert mock_send.mock_calls[0][1][0] == (
        '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
        ' xmlns="jabber:client" version="1.0" id="1" from="ecouser.net">'
    )
    # Server tells client binds
    assert mock_send.mock_calls[1][1][0] == (
        '<stream:features><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"/>'
        '<session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></stream:features>'
    )

    # Reset mock calls
    mock_send.reset_mock()

    # Send bind from "bot"
    test_data = b"<iq type='set' id='2521'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>atom</resource></bind></iq>"
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" id="2521"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind">'
        "<jid>E0000000000000001234@159.ecorobot.net/atom</jid></bind></iq>"
    )  # Bot successfully binded
    assert xmppclient.state == xmppclient.BIND  # Bot moved to BIND state

    # Reset mock calls
    mock_send.reset_mock()

    # Send set session from bot
    test_data = b"<iq type='set' id='2522'><session xmlns='urn:ietf:params:xml:ns:xmpp-session'/></iq>"
    xmppclient.parse_data(test_data)

    assert xmppclient.state == xmppclient.READY  # Bot moved to READY state
    assert mock_send.mock_calls[0][1][0] == '<iq type="result" id="2522" />'  # Bot ready

    # Reset mock calls
    mock_send.reset_mock()

    # Send presence from bot
    test_data = (
        b"<presence><status>hello world</status></presence><iq type='result'"
        b" from='E0000000000000001234@159.ecorobot.net/atom' to='ecouser.net' id='s2c1'/>"
    )
    xmppclient.parse_data(test_data)

    assert (
        mock_send.mock_calls[0][1][0] == '<presence to="E0000000000000001234@159.ecorobot.net/atom"> dummy </presence>'
    )  # bot presence - dummy response


async def test_ping_server() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.READY  # Set client state to READY
    xmppclient.uid = "E0000000000000001234"
    xmppclient.devclass = "159"
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    # Ping from bot
    test_data = (
        b'<iq xmlns:ns0="urn:xmpp:ping" from="E000BVTNX18700260382@159.ecorobot.net/atom"'
        b' id="2542" to="159.ecorobot.net" type="get"><ping /></iq>'
    )
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == '<iq type="result" id="2542" from="159.ecorobot.net" />'  # ping response


async def test_ping_client_to_client() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.READY  # Set client state to READY
    xmppclient.uid = "E0000000000000001234"
    xmppclient.devclass = "159"
    xmppclient.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)

    xmppclient2 = XMPPAsyncClient(test_transport)
    xmppclient2.state = xmppclient.READY  # Set client state to READY
    xmppclient2.uid = "fuid_tmpuser"
    xmppclient2.clientresource = "IOSF53D07BA"
    xmppclient2.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF53D07BA"
    mock_send2 = xmppclient2.send = mock.Mock(side_effect=return_send_data)

    XMPPServer.clients.append(xmppclient)
    XMPPServer.clients.append(xmppclient2)

    # Ping from user to bot
    test_data = b'<iq id="104934615" to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="get"><ping xmlns="urn:xmpp:ping" /></iq>'
    xmppclient.parse_data(test_data)

    assert mock_send2.mock_calls[0][1][0] == (
        '<iq id="104934615" to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="get"'
        ' from="E0000000000000001234@159.ecorobot.net/atom"><ping xmlns="urn:xmpp:ping" /></iq>'
    )  # ping response

    # Ping response from bot to user
    test_data = b"<iq type='result' to='E0000000000000001234@159.ecorobot.net/atom' id='104934615'/>"
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" to="E0000000000000001234@159.ecorobot.net/atom"'
        ' id="104934615" from="fuid_tmpuser@ecouser.net/IOSF53D07BA" />'
    )  # ping response


async def test_client_send_iq() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.READY  # Set client state to READY
    xmppclient.uid = "fuid_tmpuser"
    xmppclient.clientresource = "IOSF53D07BA"
    xmppclient.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF53D07BA"
    xmppclient.type = xmppclient.CONTROLLER
    mock_send = xmppclient.send = mock.Mock(side_effect=return_send_data)
    XMPPServer.clients.append(xmppclient)

    xmppclient2 = XMPPAsyncClient(test_transport)
    xmppclient2.state = xmppclient.READY  # Set client state to READY
    xmppclient2.uid = "E0000000000000001234"
    xmppclient2.devclass = "159"
    xmppclient2.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    xmppclient2.type = xmppclient2.BOT
    mock_send2 = xmppclient2.send = mock.Mock(side_effect=return_send_data)

    XMPPServer.clients.append(xmppclient2)

    # Roster IQ - Only seen from Android app so far
    test_data = b'<iq id="EE0XQ-2" type="get"><query xmlns="jabber:iq:roster" ></query></iq>'
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="error" id="EE0XQ-2"><error type="cancel" code="501"><feature-not-implemented'
        ' xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/></error></iq>'
    )  # feature not implemented response

    # Reset mock calls
    mock_send.reset_mock()

    # Bot Command
    test_data = (
        b'<iq id="7" to="E0000000000000001234@159.ecorobot.net/atom" type="set">'
        b'<query xmlns="com:ctl"><ctl id="72107787" td="GetCleanState" /></query></iq>'
    )
    xmppclient.parse_data(test_data)

    assert mock_send2.mock_calls[0][1][0] == (
        '<iq id="7" to="E0000000000000001234@159.ecorobot.net/atom" type="set" from="fuid_tmpuser@ecouser.net/IOSF53D07BA">'
        '<query xmlns="com:ctl"><ctl id="72107787" td="GetCleanState" /></query></iq>'
    )  # command was sent to bot

    # Reset mock calls
    mock_send.reset_mock()

    # Bot response to query
    test_data = (
        b'<iq xmlns:ns0="com:ctl" id="2679" to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="set">'
        b'<query><ctl td="ChargeState"><charge h="0" r="a" type="Going" /></ctl></query></iq>'
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq id="2679" to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="set" from="E0000000000000001234@159.ecorobot.net/atom">'
        '<query xmlns="com:ctl"><ctl td="ChargeState"><charge h="0" r="a" type="Going" /></ctl></query></iq>'
    )  # result sent to client

    # Reset mock calls
    mock_send.reset_mock()

    # Bot result
    test_data = b"<iq type='result' from='E0000000000000001234@159.ecorobot.net/atom' to='ecouser.net' id='s2c1'/>"
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" from="E0000000000000001234@159.ecorobot.net/atom" to="ecouser.net" id="s2c1" />'
    )  # result sent to ecouser.net

    # Reset mock calls
    mock_send.reset_mock()

    # Bot iq set
    test_data = (
        b"<iq to='fuid_tmpuser@ecouser.net/IOSF53D07BA' type='set' id='2700'><query xmlns='com:ctl'>"
        b"<ctl td='BatteryInfo'><battery power='100'/></ctl></query></iq>"
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="set" id="2700" from="E0000000000000001234@159.ecorobot.net/atom">'
        '<query xmlns="com:ctl"><ctl td="BatteryInfo"><battery power="100" /></ctl></query></iq>'
    )  # result sent to ecouser.net

    # Reset mock calls
    mock_send.reset_mock()

    # Bot error report
    test_data = (
        b"<iq to='fuid_tmpuser@ecouser.net/IOSF53D07BA' type='set' id='631'>"
        b"<query xmlns='com:ctl'><ctl td='error' errs='102'/></query></iq>"
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq to="fuid_tmpuser@ecouser.net/IOSF53D07BA" type="set" id="631" from="E0000000000000001234@159.ecorobot.net/atom">'
        '<query xmlns="com:ctl"><ctl td="error" errs="102" /></query></iq>'
    )  # result sent to ecouser.net

    # Reset mock calls
    mock_send.reset_mock()

    # Bot "DorpError" to all
    test_data = (
        b"<iq to='rl.ecorobot.net' type='set' id='1234'><query xmlns='com:sf'><sf td='pub' t='log' ts='1559893796000' tp='p'"
        b" k='DeviceAlert' v='DorpError' f='E0000000000000001234@159.ecorobot.net' g='fuid_tmpuser@ecouser.net'/></query></iq>"
    )
    xmppclient2.parse_data(test_data)
    assert mock_send.mock_calls[0][1][0] == (
        '<iq xmlns="com:sf" to="rl.ecorobot.net" type="set" id="1234" from="E0000000000000001234@159.ecorobot.net/atom">'
        '<query xmlns="com:ctl"><sf td="pub" t="log" ts="1559893796000" tp="p" k="DeviceAlert" v="DorpError"'
        ' f="E0000000000000001234@159.ecorobot.net" g="fuid_tmpuser@ecouser.net" /></query></iq>'
    )  # result sent to ecouser.net

    # Reset mock calls
    mock_send.reset_mock()
