import asyncio
import base64
import contextlib
from unittest import mock

import defusedxml.ElementTree as ET  # noqa: N817
import pytest
from testfixtures import LogCapture

from bumper.db import bot_repo, client_repo, token_repo, user_repo
from bumper.utils.settings import config as bumper_isc
from bumper.web.auth_service import generate_jwt_helper
from bumper.xmpp.xmpp import XMPPAsyncClient, XMPPServer, XMPPServerProtocol


def return_send_data(data: bytes) -> bytes:
    return data


def mock_transport_extra_info() -> tuple[str, int]:
    return ("127.0.0.1", 5223)


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_xmpp_server(xmpp_server: XMPPServer) -> None:
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_client_init() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.INIT  # Set client state to INIT
    xmppclient.uid = "fuid_tmpuser"
    xmppclient.clientresource = "IOSF00000001"
    xmppclient.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF00000001"
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
        b'<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>IOSF00000001</resource></bind></iq>'
    )
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" id="5E9872D5-547E-49AF-AE51-9EFAA282F952">'
        '<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><jid>fuid_tmpuser@ecouser.net/IOSF00000001</jid></bind></iq>'
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
        mock_send.mock_calls[0][1][0] == '<presence to="fuid_tmpuser@ecouser.net/IOSF00000001"> dummy </presence>'
    )  # client presence - dummy response


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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
        b'<iq xmlns:ns0="urn:xmpp:ping" from="E0000000000000009999@159.ecorobot.net/atom"'
        b' id="2542" to="159.ecorobot.net" type="get"><ping /></iq>'
    )
    xmppclient.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == '<iq type="result" id="2542" from="159.ecorobot.net" />'  # ping response


@pytest.mark.usefixtures("xmpp_cleanup_clients")
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
    xmppclient2.clientresource = "IOSF00000001"
    xmppclient2.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF00000001"
    mock_send2 = xmppclient2.send = mock.Mock(side_effect=return_send_data)

    XMPPServer.clients.append(xmppclient)
    XMPPServer.clients.append(xmppclient2)

    # Ping from user to bot
    test_data = b'<iq id="104934615" to="fuid_tmpuser@ecouser.net/IOSF00000001" type="get"><ping xmlns="urn:xmpp:ping" /></iq>'
    xmppclient.parse_data(test_data)

    assert mock_send2.mock_calls[0][1][0] == (
        '<iq id="104934615" to="fuid_tmpuser@ecouser.net/IOSF00000001" type="get"'
        ' from="E0000000000000001234@159.ecorobot.net/atom"><ping xmlns="urn:xmpp:ping" /></iq>'
    )  # ping response

    # Ping response from bot to user
    test_data = b"<iq type='result' to='E0000000000000001234@159.ecorobot.net/atom' id='104934615'/>"
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq type="result" to="E0000000000000001234@159.ecorobot.net/atom"'
        ' id="104934615" from="fuid_tmpuser@ecouser.net/IOSF00000001" />'
    )  # ping response


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_client_send_iq() -> None:
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    xmppclient = XMPPAsyncClient(test_transport)
    xmppclient.state = xmppclient.READY  # Set client state to READY
    xmppclient.uid = "fuid_tmpuser"
    xmppclient.clientresource = "IOSF00000001"
    xmppclient.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF00000001"
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
        '<iq id="7" to="E0000000000000001234@159.ecorobot.net/atom" type="set" from="fuid_tmpuser@ecouser.net/IOSF00000001">'
        '<query xmlns="com:ctl"><ctl id="72107787" td="GetCleanState" /></query></iq>'
    )  # command was sent to bot

    # Reset mock calls
    mock_send.reset_mock()

    # Bot response to query
    test_data = (
        b'<iq xmlns:ns0="com:ctl" id="2679" to="fuid_tmpuser@ecouser.net/IOSF00000001" type="set">'
        b'<query><ctl td="ChargeState"><charge h="0" r="a" type="Going" /></ctl></query></iq>'
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq id="2679" to="fuid_tmpuser@ecouser.net/IOSF00000001" type="set" from="E0000000000000001234@159.ecorobot.net/atom">'
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
        b"<iq to='fuid_tmpuser@ecouser.net/IOSF00000001' type='set' id='2700'><query xmlns='com:ctl'>"
        b"<ctl td='BatteryInfo'><battery power='100'/></ctl></query></iq>"
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq to="fuid_tmpuser@ecouser.net/IOSF00000001" type="set" id="2700" from="E0000000000000001234@159.ecorobot.net/atom">'
        '<query xmlns="com:ctl"><ctl td="BatteryInfo"><battery power="100" /></ctl></query></iq>'
    )  # result sent to ecouser.net

    # Reset mock calls
    mock_send.reset_mock()

    # Bot error report
    test_data = (
        b"<iq to='fuid_tmpuser@ecouser.net/IOSF00000001' type='set' id='631'>"
        b"<query xmlns='com:ctl'><ctl td='error' errs='102'/></query></iq>"
    )
    xmppclient2.parse_data(test_data)

    assert mock_send.mock_calls[0][1][0] == (
        '<iq to="fuid_tmpuser@ecouser.net/IOSF00000001" type="set" id="631" from="E0000000000000001234@159.ecorobot.net/atom">'
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


def _new_client_auth_socket() -> XMPPAsyncClient:
    """Return a client that is ready to send a SASL element."""
    test_transport = mock.Mock()
    test_transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    test_transport.write = mock.Mock(return_value=return_send_data)
    client = XMPPAsyncClient(test_transport)
    client.state = client.CONNECT
    client.send = mock.Mock(side_effect=return_send_data)
    return client


def _auth_element(username: str, password: str) -> bytes:
    """Return a PLAIN SASL element for a client name and password."""
    encoded = base64.b64encode(b"\x00" + username.encode() + b"\x00" + password.encode())
    return b'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">' + encoded + b"</auth>"


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_client_auth_code_resolves_account(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid auth code authenticates the account the older name belongs to."""
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    user_repo.add("canonical")
    user_repo.add_alias("canonical", "legacy")
    token_repo.add("canonical", "portal-token")
    token_repo.add_auth_code("canonical", "auth-code")

    client = _new_client_auth_socket()
    client.parse_data(_auth_element("legacy", "0/RESOURCE/auth-code"))

    assert client.send.mock_calls[0][1][0] == '<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    assert client.state == client.INIT
    assert client.clientresource == "RESOURCE"
    stored = client_repo.get("legacy")
    assert stored is not None
    assert stored.userid == "canonical"
    assert len(client_repo.list_all()) == 1


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_client_jwt_resolves_account(monkeypatch: pytest.MonkeyPatch) -> None:
    """A signed access token authenticates the account and adopts the older name."""
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    user_repo.add("canonical")
    token, _ = await generate_jwt_helper(data={"u": "canonical"}, t="a")

    client = _new_client_auth_socket()
    client.parse_data(_auth_element("legacy", f"0/RESOURCE/{token}"))

    assert client.send.mock_calls[0][1][0] == '<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    assert client.state == client.INIT
    stored = client_repo.get("legacy")
    assert stored is not None
    assert stored.userid == "canonical"
    assert user_repo.get_by_id("legacy").userid == "canonical"


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_client_rejects_a_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """A secret that was not issued for the account does not authenticate."""
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    user_repo.add("canonical")
    token_repo.add("canonical", "portal-token")
    token_repo.add_auth_code("canonical", "auth-code")

    client = _new_client_auth_socket()
    client.parse_data(_auth_element("canonical", "0/RESOURCE/wrong-secret"))

    assert client.send.mock_calls[0][1][0] == '<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'
    assert client.state == client.CONNECT
    assert client_repo.get("canonical") is None


def _write_transport_mock() -> mock.Mock:
    transport = mock.Mock()
    transport.__class__ = asyncio.transports.WriteTransport
    transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    transport.write = mock.Mock(return_value=return_send_data)
    return transport


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_xmpp_server_start_async_server_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    server = XMPPServer("127.0.0.1", 5223)
    loop = mock.Mock()
    msg = "boom"
    loop.create_server = mock.Mock(side_effect=RuntimeError(msg))
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: loop)
    with pytest.raises(RuntimeError):
        await server.start_async_server()


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_xmpp_server_disconnect_with_coro() -> None:
    server = XMPPServer("127.0.0.1", 5223)
    server.server = mock.Mock()
    server.server.is_serving.return_value = True
    server.server.close = mock.Mock()
    server.server.wait_closed = mock.AsyncMock()
    server.server_coro = asyncio.create_task(asyncio.sleep(10))
    await server.disconnect()
    assert server.exit_flag is True
    assert server.server_coro is None


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_protocol_tls_upgrade_connection_made() -> None:
    protocol = XMPPServerProtocol()
    client = mock.Mock()
    client.address = ("127.0.0.1", 5223)
    protocol._client = client
    transport = mock.Mock()
    protocol.connection_made(transport)
    assert client.transport is transport


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_protocol_connection_lost() -> None:
    protocol = XMPPServerProtocol()
    client = mock.Mock()
    client.address = ("127.0.0.1", 5223)
    client.bumper_jid = "jid"
    protocol._client = client
    XMPPServer.clients.append(client)
    protocol.connection_lost(None)
    assert client.set_state.called


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_client_cleanup_cancel() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.bumper_jid = "jid"

    async def dummy() -> None:
        await asyncio.sleep(10)

    task = asyncio.create_task(dummy())
    client.schedule_ping_task = task
    client.cleanup()
    assert task.cancelled() or task.cancelling() > 0


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_send_not_write_transport() -> None:
    transport = mock.Mock()
    transport.get_extra_info = mock.Mock(return_value=mock_transport_extra_info())
    client = XMPPAsyncClient(transport)
    # transport is not a WriteTransport, send should return early
    client.send.__wrapped__ if hasattr(client.send, "__wrapped__") else None
    client.send = XMPPAsyncClient.send.__get__(client, XMPPAsyncClient)
    client.send("<ping/>")
    transport.write.assert_not_called()


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_send_debug_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bumper_isc, "DEBUG_LOGGING_XMPP_RESPONSE", True)
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.send("<ping/>")
    transport.write.assert_called()


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_send_exception() -> None:
    transport = _write_transport_mock()
    transport.write.side_effect = RuntimeError("boom")
    client = XMPPAsyncClient(transport)
    client.send("<ping/>")
    # no raise


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_disconnect_bot_and_client() -> None:

    transport = _write_transport_mock()
    # bot
    bot_client = XMPPAsyncClient(transport)
    bot_client.uid = "E0000000000000001234"
    bot_client.devclass = "159"
    bot_client.clientresource = ""
    bot_repo.add(bot_client.uid, bot_client.uid, bot_client.devclass, "atom", "eco-legacy")
    bot_client.disconnect()
    transport.close.assert_called()

    transport2 = _write_transport_mock()
    ctrl = XMPPAsyncClient(transport2)
    ctrl.uid = "fuid_tmpuser"
    ctrl.devclass = ""
    ctrl.clientresource = "IOSF00000001"
    client_repo.add(ctrl.uid, ctrl.uid, "USER", ctrl.clientresource)
    ctrl.disconnect()
    transport2.close.assert_called()


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_disconnect_exception() -> None:
    transport = _write_transport_mock()
    transport.close.side_effect = RuntimeError("boom")
    client = XMPPAsyncClient(transport)
    client.disconnect()  # no raise


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_tag_strip_uri_exception() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    assert client._tag_strip_uri(123) == 123  # type: ignore[arg-type]


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_set_state_illegal_and_exception() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.state = client.READY
    client.set_state("CONNECT")  # illegal, logged
    # state unchanged? set_state swallows
    client.set_state("NONEXISTENT")  # exception, logged


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_ctl_branches() -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "fuid_tmpuser"
    client.bumper_jid = "fuid_tmpuser@ecouser.net/IOSF00000001"
    client.type = client.CONTROLLER
    client.send = mock.Mock(side_effect=return_send_data)

    # roster
    xml = ET.fromstring('<iq id="r1" type="get"><query xmlns="jabber:iq:roster"/></iq>')
    client._handle_ctl(xml, "roster query")
    assert "feature-not-implemented" in client.send.mock_calls[0][1][0]

    client.send.reset_mock()
    # disco#items
    xml = ET.fromstring('<iq id="d1" type="get"><query node="http://jabber.org/protocol/disco#items"/></iq>')
    client._handle_ctl(xml, "disco#items")
    assert "feature-not-implemented" in client.send.mock_calls[0][1][0]

    client.send.reset_mock()
    # disco#info
    xml = ET.fromstring('<iq id="i1" type="get"><query node="http://jabber.org/protocol/disco#info"/></iq>')
    client._handle_ctl(xml, "disco#info")
    assert "feature-not-implemented" in client.send.mock_calls[0][1][0]

    client.send.reset_mock()
    # com:sf set to rl.ecorobot.net
    xml = ET.fromstring(
        '<iq id="s1" to="rl.ecorobot.net" type="set"><query xmlns="com:sf"><sf td="pub"/></query></iq>',
    )
    client._handle_ctl(xml, "com:sf")
    # no send? It sends result
    # just no exception

    # admin from bot
    client.type = client.BOT
    client.send.reset_mock()
    xml = ET.fromstring(
        '<iq id="a1" type="set"><query xmlns="com:ctl"><ctl admin="adminuser"/></query></iq>',
    )
    client._handle_ctl(xml, "admin data")
    # returns without send

    # exception
    client._handle_ctl(None, "data")  # type: ignore[arg-type]


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_ping_branches() -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "E0000000000000001234"
    client.devclass = "159"
    client.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    client.type = client.BOT
    client.state = client.READY
    client.send = mock.Mock(side_effect=return_send_data)

    # server ping (no @)
    xml = ET.fromstring('<iq id="p1" to="159.ecorobot.net" type="get"><ping xmlns="urn:xmpp:ping"/></iq>')
    client._handle_ping(xml)
    assert 'type="result"' in client.send.mock_calls[0][1][0]

    client.send.reset_mock()
    # exception
    client._handle_ping(None)  # type: ignore[arg-type]


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_schedule_ping_exception() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "u"
    client.bumper_jid = "u@ecouser.net"
    client.state = client.READY

    def boom() -> None:
        client.state = client.DISCONNECT
        msg = "boom"
        raise RuntimeError(msg)

    client.send = mock.Mock(side_effect=boom)
    await client.schedule_ping(10)


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_schedule_ping_cancel() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "u"
    client.bumper_jid = "u@ecouser.net"
    client.state = client.READY
    client.send = mock.Mock(side_effect=return_send_data)

    async def run() -> None:
        await client.schedule_ping(10)

    task = asyncio.create_task(run())
    await asyncio.sleep(0)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await task


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_handle_result_errno_and_permission(monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr(bumper_isc, "USE_AUTH", False)

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "E0000000000000001234"
    client.devclass = "159"
    client.type = client.BOT
    client.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    client.send = mock.Mock(side_effect=return_send_data)

    # errno in data (not 103)
    xml = ET.fromstring(
        '<iq id="e1" to="fuid_tmpuser@ecouser.net/RES" type="set"><query xmlns="com:ctl"><ctl td="x" errno="5"/></query></iq>',
    )
    client._handle_result(xml, "errno='5'")

    # permission denied 103 with error attr
    xml = ET.fromstring(
        '<iq id="e2" to="fuid_tmpuser@ecouser.net/RES" type="set">'
        '<query xmlns="com:ctl"><ctl td="x" error="permission denied, please contact adminuser"/></query></iq>',
    )
    client._handle_result(xml, "errno='103'")
    # sends adduser etc
    assert client.send.call_count >= 1

    # permission denied with admin attr
    client.send.reset_mock()
    xml = ET.fromstring(
        '<iq id="e3" to="fuid_tmpuser@ecouser.net/RES" type="set">'
        '<query xmlns="com:ctl"><ctl td="x" admin="adminuser"/></query></iq>',
    )
    client._handle_result(xml, "errno='103'")
    assert client.send.call_count >= 1


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_result_de_ecorobot_and_forward() -> None:

    transport = _write_transport_mock()
    bot = XMPPAsyncClient(transport)
    bot.uid = "E0000000000000001234"
    bot.devclass = "159"
    bot.type = bot.BOT
    bot.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    bot.send = mock.Mock(side_effect=return_send_data)

    transport2 = _write_transport_mock()
    ctrl = XMPPAsyncClient(transport2)
    ctrl.uid = "fuid_tmpuser"
    ctrl.type = ctrl.CONTROLLER
    ctrl.state = ctrl.READY
    ctrl.bumper_jid = "fuid_tmpuser@ecouser.net/RES"
    ctrl.send = mock.Mock(side_effect=return_send_data)

    XMPPServer.clients.append(bot)
    XMPPServer.clients.append(ctrl)

    # de.ecorobot.net send to all
    xml = ET.fromstring(
        '<iq id="d1" to="de.ecorobot.net" type="set"><query xmlns="com:ctl"><ctl td="x"/></query></iq>',
    )
    bot._handle_result(xml, "noerrno")

    # forward to matching client
    xml = ET.fromstring(
        '<iq id="f1" to="fuid_tmpuser@ecouser.net/RES" type="set"><query xmlns="com:ctl"><ctl td="x"/></query></iq>',
    )
    bot._handle_result(xml, "noerrno")
    assert ctrl.send.called

    XMPPServer.clients.clear()


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_result_exception() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.type = client.BOT
    xml = ET.fromstring('<iq id="x" to="a@b/c" type="set"><query xmlns="com:ctl"/></iq>')
    client._handle_result(xml, "errno='103'")


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_connect_branches() -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.state = client.CONNECT
    client.send = mock.Mock(side_effect=return_send_data)

    # no jabber:client -> close stream
    client._handle_connect("foo bar", None)
    assert client.send.mock_calls[0][1][0] == "</stream>"

    client.send.reset_mock()
    # auth ns branch
    xml = ET.fromstring('<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">AAAA</auth>')
    # make xml tag contain ns
    client._handle_connect("x", xml)
    # sasl auth called; xml_text not None maybe parts <2 -> send response
    # no assertion strict

    client.send.reset_mock()
    # error branch
    xml2 = ET.fromstring("<foo/>")
    client._handle_connect("x", xml2)

    # INIT state branches
    client.state = client.INIT
    client.send.reset_mock()
    # stream
    client._handle_connect("<stream:stream xmlns='jabber:client'/>", None)
    assert client.send.call_count == 2

    client.send.reset_mock()
    # bind
    xml3 = ET.fromstring('<iq type="set"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>R</resource></bind></iq>')
    client.uid = "u"
    client.devclass = ""
    client.clientresource = "R"
    client.bumper_jid = "u@ecouser.net/R"
    client._handle_connect("x", xml3)
    assert client.state == client.BIND

    client.send.reset_mock()
    # non-bind iq -> error log
    xml4 = ET.fromstring("<iq><foo/></iq>")
    client._handle_connect("x", xml4)


@pytest.mark.usefixtures("test_files", "xmpp_cleanup_clients")
async def test_handle_starttls(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.tls_upgraded = False
    proto = mock.Mock()
    transport.get_protocol = mock.Mock(return_value=proto)
    loop = mock.Mock()
    loop.start_tls = mock.AsyncMock(return_value=transport)
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: loop)
    await client._handle_starttls()
    assert client.tls_upgraded is True

    # already upgraded early return
    client2 = XMPPAsyncClient(_write_transport_mock())
    client2.tls_upgraded = True
    await client2._handle_starttls()

    # exception path
    transport3 = _write_transport_mock()
    client3 = XMPPAsyncClient(transport3)
    client3.tls_upgraded = False
    proto3 = mock.Mock()
    transport3.get_protocol = mock.Mock(return_value=proto3)
    loop3 = mock.Mock()
    loop3.start_tls = mock.AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: loop3)
    await client3._handle_starttls()  # no raise


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_handle_sasl_auth_branches(monkeypatch: pytest.MonkeyPatch) -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.state = client.CONNECT
    client.send = mock.Mock(side_effect=return_send_data)

    # xml_text None
    xml = ET.fromstring('<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN"/>')
    client._handle_sasl_auth(xml)

    # parts < 2
    encoded = base64.b64encode(b"useronly")
    xml2 = ET.fromstring(
        f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{encoded.decode()}</auth>',
    )
    client._handle_sasl_auth(xml2)

    # exception
    client._handle_sasl_auth(None)  # type: ignore[arg-type]

    # bot branch with password parts
    client2 = XMPPAsyncClient(_write_transport_mock())
    client2.state = client2.CONNECT
    client2.devclass = "159"
    client2.uid = ""
    client2.send = mock.Mock(side_effect=return_send_data)
    # password with 3 parts
    secret = "0/RESOURCE/secret"  # noqa: S105
    encoded2 = base64.b64encode(b"\x00E0000000000000001234\x00" + secret.encode())
    xml3 = ET.fromstring(
        f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{encoded2.decode()}</auth>',
    )
    client2._handle_sasl_auth(xml3)
    assert client2.type == client2.BOT

    # client auth failure path (wrong secret) with USE_AUTH
    monkeypatch.setattr(bumper_isc, "USE_AUTH", True)
    user_repo.add("canonical")

    token_repo.add("canonical", "portal-token")
    token_repo.add_auth_code("canonical", "auth-code")
    client3 = XMPPAsyncClient(_write_transport_mock())
    client3.state = client3.CONNECT
    client3.send = mock.Mock(side_effect=return_send_data)
    encoded3 = base64.b64encode(b"\x00canonical\x000/RESOURCE/wrong")
    xml4 = ET.fromstring(
        f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{encoded3.decode()}</auth>',
    )
    client3._handle_sasl_auth(xml4)
    assert client3.send.mock_calls[0][1][0] == '<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>'


@pytest.mark.usefixtures("clean_database", "xmpp_cleanup_clients")
async def test_handle_bind_branches(monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr(bumper_isc, "USE_AUTH", False)

    # bot with no bot in db (get None) -> skip set_xmpp
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "E0000000000000001234"
    client.devclass = "159"
    client.type = client.BOT
    client.state = client.INIT
    client.send = mock.Mock(side_effect=return_send_data)
    xml = ET.fromstring("<iq id='b1'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>atom</resource></bind></iq>")
    client._handle_bind(xml)
    assert client.bumper_jid == "E0000000000000001234@159.ecorobot.net/atom"

    # client with no resource element -> else branch name/address
    transport2 = _write_transport_mock()
    client2 = XMPPAsyncClient(transport2)
    client2.uid = "fuid_tmpuser"
    client2.devclass = ""
    client2.type = client2.CONTROLLER
    client2.account_user_id = "fuid_tmpuser"
    client2.state = client2.INIT
    client2.send = mock.Mock(side_effect=return_send_data)
    xml2 = ET.fromstring("<iq id='b2'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'/></iq>")
    client2._handle_bind(xml2)
    assert "fuid_tmpuser@ecouser.net" in client2.bumper_jid

    # client with account_user_id and resource -> add + set_xmpp
    transport3 = _write_transport_mock()
    client3 = XMPPAsyncClient(transport3)
    client3.uid = "fuid_tmpuser2"
    client3.devclass = ""
    client3.type = client3.CONTROLLER
    client3.account_user_id = "fuid_tmpuser2"
    client3.clientresource = "RES"
    client3.state = client3.INIT
    client3.send = mock.Mock(side_effect=return_send_data)
    xml3 = ET.fromstring(
        "<iq id='b3'><bind xmlns='urn:ietf:params:xml:ns:xmpp-bind'><resource>RES</resource></bind></iq>",
    )
    client3._handle_bind(xml3)
    assert client_repo.get("fuid_tmpuser2", resource="RES") is not None

    # exception
    client3._handle_bind(None)  # type: ignore[arg-type]


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_presence_branches() -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "E0000000000000001234"
    client.devclass = "159"
    client.bumper_jid = "E0000000000000001234@159.ecorobot.net/atom"
    client.type = client.BOT
    client.state = client.READY
    client.send = mock.Mock(side_effect=return_send_data)

    # status present
    xml = ET.fromstring("<presence><status>hello</status></presence>")
    client._handle_presence(xml)
    assert client.send.called

    client.send.reset_mock()
    client.type = client.CONTROLLER
    # available
    xml2 = ET.fromstring('<presence type="available"/>')
    client._handle_presence(xml2)
    assert client.send.called

    client.send.reset_mock()
    # unavailable
    xml3 = ET.fromstring('<presence type="unavailable"/>')
    client._handle_presence(xml3)
    assert client.state == client.DISCONNECT

    client2 = XMPPAsyncClient(_write_transport_mock())
    client2.uid = "u"
    client2.bumper_jid = "u@ecouser.net"
    client2.type = client2.CONTROLLER
    client2.state = client2.READY
    client2.send = mock.Mock(side_effect=return_send_data)
    # unknown type
    xml4 = ET.fromstring("<presence/>")
    client2._handle_presence(xml4)
    assert client2.send.called


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_parse_data_branches(monkeypatch: pytest.MonkeyPatch) -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "u"
    client.bumper_jid = "u@ecouser.net"
    client.state = client.CONNECT
    client.send = mock.Mock(side_effect=return_send_data)

    monkeypatch.setattr(bumper_isc, "DEBUG_LOGGING_XMPP_REQUEST_ORIGINAL", True)
    monkeypatch.setattr(bumper_isc, "DEBUG_LOGGING_XMPP_REQUEST_REFACTORED", True)

    # xml declaration strip
    data = b"<?xml version='1.0'?><stream:stream xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' />"
    client.parse_data(data)
    assert client.send.called

    client.send.reset_mock()
    # invalid xml -> parse error
    client.parse_data(b"<bad><unclosed>")
    # no raise

    client.send.reset_mock()
    # unparsed item
    client.state = client.CONNECT
    client.parse_data(b"<foo/>")
    # warning logged, no raise

    client.send.reset_mock()
    # end stream only
    client.parse_data(b"</stream:stream>")
    assert client.send.called

    client.send.reset_mock()
    # starttls item
    client.tls_upgraded = False
    client.state = client.CONNECT
    # send stream first to set state? just call
    client.parse_data(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
    # utils.store_service called; no raise


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_handle_iq_branches() -> None:

    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "u"
    client.bumper_jid = "u@ecouser.net"
    client.type = client.CONTROLLER
    client.state = client.READY
    client.send = mock.Mock(side_effect=return_send_data)

    # non-iq tag -> skip
    xml = ET.fromstring("<foo/>")
    client._handle_iq(xml, "data")

    # iq with child ping
    xml2 = ET.fromstring('<iq id="p"><ping xmlns="urn:xmpp:ping"/></iq>')
    client._handle_iq(xml2, "data")

    # iq result type
    xml3 = ET.fromstring('<iq type="result" id="r"/>')
    client._handle_iq(xml3, "data")

    # to_dict
    d = client.to_dict()
    assert d["uid"] == "u"


@pytest.mark.usefixtures("xmpp_cleanup_clients")
async def test_xml_replacer_and_to_dict() -> None:
    transport = _write_transport_mock()
    client = XMPPAsyncClient(transport)
    client.uid = "u"
    client.bumper_jid = "u@ecouser.net"

    el = ET.fromstring('<iq xmlns="com:ctl"><query/></iq>')
    out = client._xml_replacer(el, "query", "com:ctl")
    assert "xmlns" in out
    assert client.to_dict()["state"] in (0, 1, 2, 3, 4, 5)
