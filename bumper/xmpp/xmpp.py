"""XMPP module."""

import asyncio
from asyncio import Task, transports
import base64
import logging
import re
import ssl
from typing import Any
import uuid
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET  # noqa: N817

from bumper.utils import db, utils
from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)
_LOGGER_CLIENT = logging.getLogger(f"{__name__}.client")


class XMPPServer:
    """XMPP server."""

    server_id: str = "ecouser.net"
    clients: list["XMPPAsyncClient"] = []
    exit_flag: bool = False
    server: asyncio.Server | None = None

    def __init__(self, host: str, port: int) -> None:
        """XMPP server init."""
        # Initialize bot server
        self._host = host
        self._port = port
        self.xmpp_protocol = XMPPServerProtocol
        self.server_coro: Task[None] | None = None

    async def start_async_server(self) -> None:
        """Start server."""
        try:
            _LOGGER.info(f"Starting XMPP Server at {self._host}:{self._port}")
            loop = asyncio.get_running_loop()
            self.server = await loop.create_server(self.xmpp_protocol, host=self._host, port=self._port)
        except Exception:
            _LOGGER.exception(utils.default_exception_str_builder())
            raise

    async def disconnect(self) -> None:
        """Disconnect."""
        _LOGGER.info("Shutting down XMPP Server...")

        _LOGGER.debug("waiting for all clients to disconnect")
        for client in self.clients:
            client.disconnect()

        self.exit_flag = True
        if self.server is not None and self.server.is_serving():
            self.server.close()
            await self.server.wait_closed()
        _LOGGER.debug("shutting down")
        if self.server_coro is not None:
            self.server_coro.cancel()


class XMPPServerProtocol(asyncio.Protocol):
    """XMPP server protocol."""

    client_id: str | None = None
    exit_flag: bool = False
    _client: "XMPPAsyncClient | None" = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        """Establish connection."""
        if self._client:  # Existing client... upgrading to TLS
            _LOGGER.debug(f"Upgraded connection for {self._client.address}")
            self._client.transport = transport
        else:
            client = XMPPAsyncClient(transport)
            self._client = client
            XMPPServer.clients.append(client)
            self._client.state = client.CONNECT
            _LOGGER.debug(f"New Connection from {client.address}")

    def connection_lost(self, _: Exception | None) -> None:
        """Lost connection."""
        if self._client is not None:
            XMPPServer.clients.remove(self._client)
            self._client.set_state("DISCONNECT")
            _LOGGER.debug(f"End Connection for ({self._client.address[0]}:{self._client.address[1]} | {self._client.bumper_jid})")

    def data_received(self, data: bytes) -> None:
        """Parse received data."""
        if self._client is not None:
            self._client.parse_data(data)


class XMPPAsyncClient:
    """XMPP client."""

    IDLE: int = 0
    CONNECT: int = 1
    INIT: int = 2
    BIND: int = 3
    READY: int = 4
    DISCONNECT: int = 5
    UNKNOWN: int = 0
    BOT: int = 1
    CONTROLLER: int = 2
    tls_upgraded: bool = False
    schedule_ping_task: asyncio.Task[Any] | None = None  # Track the schedule_ping task

    def __init__(self, transport: transports.BaseTransport) -> None:
        """XMPP client init."""
        self.type = self.UNKNOWN
        self.state = self.IDLE
        self.address = transport.get_extra_info("peername")
        self.transport = transport
        self.clientresource: str | None = ""
        self.devclass = ""
        self.bumper_jid = ""
        self.uid = ""
        self.name: str | None = None
        self.log_sent_message: bool = True  # Set to true to log sends
        self.log_incoming_data: bool = True  # Set to true to log sends
        _LOGGER_CLIENT.debug(f"new client with ip {self.address}")

    def cleanup(self) -> None:
        """Ensure proper cleanup of the schedule_ping_task."""
        if self.schedule_ping_task and not self.schedule_ping_task.done():
            self.schedule_ping_task.cancel()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self.schedule_ping_task = asyncio.ensure_future(self.schedule_ping_task)
                else:
                    loop.run_until_complete(self.schedule_ping_task)
            except (asyncio.CancelledError, RuntimeError):
                _LOGGER_CLIENT.debug(f"Ping task canceled for {self.bumper_jid}")

    def send(self, command: str) -> None:
        """Send command."""
        try:
            command = command.replace('"', "'")
            if self.log_sent_message:
                _LOGGER_CLIENT.debug(f"send to ({self.address[0]}:{self.address[1]} | {self.bumper_jid}) - {command}")
            if isinstance(self.transport, transports.WriteTransport):
                if bumper_isc.DEBUG_LOGGING_XMPP_RESPONSE is True:
                    _LOGGER_CLIENT.info(f"SENDING  :: {command}")
                self.transport.write(command.encode())
        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def disconnect(self) -> None:
        """Disconnect."""
        _LOGGER.info("Disconnect XMPP Client...")
        try:
            self.cleanup()  # Ensure the ping task is cleaned up
            bot = db.bot_get(self.uid)
            if bot:
                db.bot_set_xmpp(bot.get("did"), False)
            if self.clientresource is not None:
                client = db.client_get(self.clientresource)
                if client:
                    db.client_set_xmpp(client.get("resource"), False)
            self.transport.close()
        except Exception:
            _LOGGER_CLIENT.error(utils.default_exception_str_builder(), exc_info=True)

    def _tag_strip_uri(self, tag: str) -> str:
        try:
            if tag[0] == "{":
                _, _, tag = tag[1:].partition("}")
        except Exception:
            _LOGGER_CLIENT.error(utils.default_exception_str_builder(), exc_info=True)
        return tag

    def set_state(self, state: str) -> None:
        """Set state."""
        try:
            new_state = getattr(XMPPAsyncClient, state)
            if self.state > new_state:
                msg = f"{self.address} illegal state change {self.state}->{new_state}"
                raise Exception(msg)
            _LOGGER_CLIENT.debug(f"({self.address[0]}:{self.address[1]} | {self.bumper_jid}) state: {state}")
            self.state = new_state
            if new_state == 5:
                self.disconnect()
        except Exception:
            _LOGGER_CLIENT.error(utils.default_exception_str_builder(), exc_info=True)

    def _handle_ctl(self, xml: Element, data: str) -> None:
        try:
            if "roster" in data:
                # Return not-implemented for roster
                self.send(
                    f'<iq type="error" id="{xml.get("id")}"><error type="cancel" code="501">'
                    '<feature-not-implemented xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/></error></iq>',
                )
                return

            if "disco#items" in data:
                # Return  not-implemented for disco#items
                self.send(
                    f'<iq type="error" id="{xml.get("id")}"><error type="cancel" code="501">'
                    '<feature-not-implemented xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/></error></iq>',
                )
                return

            if "disco#info" in data:
                # Return not-implemented for disco#info
                self.send(
                    f'<iq type="error" id="{xml.get("id")}"><error type="cancel" code="501">'
                    '<feature-not-implemented xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/></error></iq>',
                )
                return

            # Android bind? Not sure what this does yet.
            if xml.get("type") == "set" and "com:sf" in data and xml.get("to") == "rl.ecorobot.net":
                self.send(
                    f'<iq id="{xml.get("id")}" to="{self.uid}@{XMPPServer.server_id}/{self.clientresource}"'
                    ' from="rl.ecorobot.net" type="result"/>',
                )

            if len(xml[0]) > 0:
                ctl = xml[0][0]
                if ctl.get("admin") and self.type == self.BOT:
                    _LOGGER_CLIENT.debug(
                        f"admin username received from bot: {ctl.get('admin')}",
                    )
                    # XMPPServer_Protocol.client_id = ctl.get("admin")
                    return

            # forward
            for client in XMPPServer.clients:
                if client.bumper_jid != self.bumper_jid and client.state == client.READY:
                    ctl_to = xml.get("to")
                    if "from" not in xml.attrib:
                        xml.attrib["from"] = self.bumper_jid
                    # clean up string to remove namespaces added by ET
                    rxmlstring = self._xml_replacer(xml, "query", "com:ctl")

                    if client.type == self.BOT and ctl_to is not None and client.uid.lower() in ctl_to.lower():
                        _LOGGER_CLIENT.debug(
                            f"Sending ctl to bot: {rxmlstring}",
                        )
                        client.send(rxmlstring)

        except Exception:
            _LOGGER_CLIENT.error(utils.default_exception_str_builder(), exc_info=True)

    def _handle_ping(self, xml: Element) -> None:
        try:
            pingto = xml.get("to")

            if pingto is not None and pingto.find("@") == -1:  # No to address
                # Ping to server - respond
                pingresp = f'<iq type="result" id="{xml.get("id")}" from="{pingto}" />'
                self.send(pingresp)

            else:
                pingfrom = self.bumper_jid
                if "from" not in xml.attrib:
                    xml.attrib["from"] = pingfrom
                # clean up string to remove namespaces added by ET
                pingstring = self._xml_replacer(xml, "ping", "urn:xmpp:ping")

                for client in XMPPServer.clients:
                    if (
                        pingto is not None
                        and client.bumper_jid != self.bumper_jid
                        and client.state == client.READY
                        and client.uid.lower() in pingto.lower()
                    ):
                        client.send(pingstring)

        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    async def schedule_ping(self, time: float) -> None:
        """Schedule ping."""
        try:
            while self.state != self.DISCONNECT:  # Run only if not disconnected
                self.send(
                    f"<iq from='{XMPPServer.server_id}' to='{self.bumper_jid}' id='s2c1' type='get'>"
                    " <ping xmlns='urn:xmpp:ping'/></iq>",
                )
                await asyncio.sleep(time)
        except asyncio.CancelledError:
            _LOGGER_CLIENT.debug(f"Ping task canceled for {self.bumper_jid}")
        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def _handle_result(self, xml: Element, data: str) -> None:
        try:
            ctl_to = xml.get("to")
            if "from" not in xml.attrib:
                xml.attrib["from"] = self.bumper_jid
            if "errno" in data:
                _LOGGER_CLIENT.error(f"Error from bot :: {data}")

            # NOTE: possible errno='5' is happen after sensor error and the bot will be on without further possible interactions,
            # manual button interaction current needed

            # No permissions, usually if bot was last on Ecovac network, Bumper will try to add fuid user as owner
            if "errno='103'" in data:
                if self.type == self.BOT:
                    _LOGGER_CLIENT.info(
                        "Bot reported user has no permissions, Bumper will attempt to add user to bot. "
                        "This is typical if bot was last on Ecovacs Network.",
                    )
                    ctl = list(next(iter(xml)))
                    adminuser = None
                    if "error" in ctl[0].attrib:
                        ctlerr = ctl[0].attrib["error"]
                        adminuser = ctlerr.replace("permission denied, please contact ", "")
                        adminuser = adminuser.replace(" ", "")
                    elif "admin" in ctl[0].attrib:
                        adminuser = ctl[0].attrib["admin"]
                    if (
                        ctl_to is not None
                        and adminuser is not None
                        and not (adminuser.startswith(("fuid_", "fusername_")) or bumper_isc.USE_AUTH)
                    ):  # if not fuid_ then its ecovacs OR ignore bumper auth
                        # NOTE: Implement auth later, should this user have access to bot?

                        # Add user jid to bot
                        newuser = ctl_to.split("/")[0]
                        adduser = (
                            f'<iq type="set" id="{uuid.uuid4()}" from="{adminuser}" to="{self.bumper_jid}">'
                            f'<query xmlns="com:ctl"><ctl td="AddUser" id="0000" jid="{newuser}" /></query></iq>'
                        )
                        _LOGGER_CLIENT.debug(f"Adding User to bot - {adduser}")
                        self.send(adduser)

                        # Add user ACs - Manage users, settings, and clean (full access)
                        adduseracs = (
                            f'<iq type="set" id="{uuid.uuid4()}" from="{adminuser}" to="{self.bumper_jid}">'
                            f'<query xmlns="com:ctl"><ctl td="SetAC" id="1111" jid="{newuser}"><acs>'
                            '<ac name="userman" allow="1"/><ac name="setting" allow="1"/><ac name="clean" allow="1"/>'
                            "</acs></ctl></query></iq>"
                        )
                        _LOGGER_CLIENT.debug(
                            f"Add User ACs to bot - {adduseracs}",
                        )
                        self.send(adduseracs)

                        # GetUserInfo - Just to confirm it set correctly
                        self.send(
                            f'<iq type="set" id="{uuid.uuid4()}" from="{adminuser}" to="{self.bumper_jid}">'
                            '<query xmlns="com:ctl"><ctl td="GetUserInfo" id="4444" /><UserInfos/></query></iq>',
                        )

            else:
                rxmlstring = self._xml_replacer(xml, "query", "com:ctl")
                if self.type == self.BOT and ctl_to == "de.ecorobot.net":  # Send to all clients
                    _LOGGER_CLIENT.debug(f"Sending to all clients because of de: {rxmlstring}")
                    for client in XMPPServer.clients:
                        client.send(rxmlstring)

                if ctl_to is not None and ctl_to.find("@") != -1:  # address Found
                    ctl_to = f"{ctl_to.split('@')[0]}@ecouser.net"

                for client in XMPPServer.clients:
                    if client.bumper_jid != self.bumper_jid and client.state == client.READY:
                        if ctl_to is None or "@" not in ctl_to:  # No user@, send to all clients?
                            # NOTE: Revisit later, this may be wrong
                            client.send(rxmlstring)
                        elif client.uid.lower() in ctl_to.lower():  # If client matches TO=
                            _LOGGER_CLIENT.debug(f"Sending from {self.uid} to client {client.uid}: {rxmlstring}")
                            client.send(rxmlstring)
        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(info=ET.tostring(xml).decode("utf-8")), exc_info=True)

    def _handle_connect(self, xml_str: str, xml: Element | None = None) -> None:
        try:
            if self.state == self.CONNECT:
                if xml is None:
                    # Client first connecting, send our features
                    if xml_str.find("jabber:client") > -1:
                        sc = xml_str.find("to=")
                        ec = xml_str.find(".ecorobot.net")
                        if ec > -1:
                            self.devclass = xml_str[sc + 4 : ec]
                        # ack jabbr:client
                        # Send stream tag to client, acknowledging connection
                        self.send(
                            '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
                            f' xmlns="jabber:client" version="1.0" id="1" from="{XMPPServer.server_id}">',
                        )

                        # Send STARTTLS to client with auth mechanisms
                        if self.tls_upgraded is False:
                            # With STARTTLS #https://xmpp.org/rfcs/rfc3920.html
                            self.send(
                                '<stream:features><starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"><required/></starttls>'
                                '<mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl"><mechanism>PLAIN</mechanism></mechanisms>'
                                "</stream:features>",
                            )

                        else:
                            # Already using TLS send authentication support for SASL
                            self.send(
                                '<stream:features><mechanisms xmlns="urn:ietf:params:xml:ns:xmpp-sasl">'
                                "<mechanism>PLAIN</mechanism></mechanisms></stream:features>",
                            )

                    else:
                        self.send("</stream>")
                elif "urn:ietf:params:xml:ns:xmpp-sasl" in xml.tag:  # Handle SASL Auth
                    self._handle_sasl_auth(xml)
                else:
                    _LOGGER_CLIENT.error(f"Couldn't handle :: {xml}")

            elif self.state == self.INIT:
                if xml is None:
                    # Client getting session after authentication
                    if xml_str.find("jabber:client") > -1:
                        # ack jabbr:client
                        self.send(
                            '<stream:stream xmlns:stream="http://etherx.jabber.org/streams"'
                            f' xmlns="jabber:client" version="1.0" id="1" from="{XMPPServer.server_id}">',
                        )

                        self.send(
                            '<stream:features><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"/>'
                            '<session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></stream:features>',
                        )

                else:  # Handle init bind
                    child = self._tag_strip_uri(xml[0].tag) if len(xml) else None

                    if xml.tag == "iq":
                        if child == "bind":
                            self._handle_bind(xml)
                    else:
                        _LOGGER_CLIENT.error(f"Couldn't handle :: {xml}")

        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    async def _handle_starttls(self) -> None:
        try:
            if self.tls_upgraded is True:
                return

            self.tls_upgraded = True  # Set TLSUpgraded true to prevent further attempts to upgrade connection
            _LOGGER_CLIENT.debug(f"Upgrading connection with STARTTLS for {self.address[0]}:{self.address[1]}")
            self.send("<proceed xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")  # send process to client

            # After proceed the connection should be upgraded to TLS
            loop = asyncio.get_event_loop()
            transport = self.transport
            protocol = self.transport.get_protocol()

            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(bumper_isc.server_cert, bumper_isc.server_key)
            ssl_ctx.load_verify_locations(cafile=bumper_isc.ca_cert)

            if isinstance(transport, transports.WriteTransport):
                new_transport = await loop.start_tls(transport, protocol, ssl_ctx, server_side=True)
                if new_transport is not None:
                    protocol.connection_made(new_transport)

        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def _handle_sasl_auth(self, xml: Element) -> None:
        try:
            xml_text = xml.text
            if xml_text is None:
                _LOGGER_CLIENT.debug("xml text is None!")
                return

            saslauth = base64.b64decode(xml_text).decode("utf-8").split("/")
            username = saslauth[0]
            username = saslauth[0].split("\x00")[1]
            authcode = ""
            self.uid = username
            if len(saslauth) > 1:
                resource = saslauth[1]
                self.clientresource = resource
            elif len(saslauth[0].split("\x00")) > 2:
                resource = saslauth[0].split("\x00")[2]
                self.clientresource = resource

            if len(saslauth) > 2:
                authcode = saslauth[2]

            if self.devclass:  # if there is a devclass it is a bot
                db.bot_add(self.uid, self.uid, self.devclass, "atom", "eco-legacy")
                self.type = self.BOT
                _LOGGER_CLIENT.info(f"bot authenticated SN :: {self.uid}")
                # Send response
                self.send('<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>')  # Success
                # Client authenticated, move to next state
                self.set_state("INIT")

            else:
                auth = False
                if db.check_auth_code(self.uid, authcode) or bumper_isc.USE_AUTH is False:
                    auth = True

                if auth and self.clientresource is not None:
                    self.type = self.CONTROLLER
                    db.client_add(self.uid, "bumper", self.clientresource)
                    _LOGGER_CLIENT.info(f"client authenticated :: {self.uid}")
                    # Client authenticated, move to next state
                    self.set_state("INIT")
                    # Send response
                    self.send('<success xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>')  # Success
                else:
                    # Failed to authenticate
                    self.send('<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl"/>')  # Fail

        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def _handle_bind(self, xml: Element) -> None:
        try:
            bot = db.bot_get(self.uid)
            if bot:
                db.bot_set_xmpp(bot.get("did"), True)

            if self.clientresource is not None:
                client = db.client_get(self.clientresource)
                if client is not None:
                    db.client_set_xmpp(client["resource"], True)

            type_added = "client"
            clientresourcexml = list(next(iter(xml)))
            if self.devclass:  # its a bot
                self.name = f"XMPP_Client_{self.uid}_{self.devclass}"
                self.bumper_jid = f"{self.uid}@{self.devclass}.ecorobot.net/atom"
                type_added = "bot"
            elif len(clientresourcexml) > 0:
                self.clientresource = clientresourcexml[0].text
                self.name = f"XMPP_Client_{self.clientresource}"
                self.bumper_jid = f"{self.uid}@{XMPPServer.server_id}/{self.clientresource}"
            else:
                self.name = f"XMPP_Client_{self.uid}_{self.address}"
                self.bumper_jid = f"{self.uid}@{XMPPServer.server_id}"

            _LOGGER_CLIENT.debug(f"new {type_added} ({self.address[0]}:{self.address[1]} | {self.bumper_jid})")
            res = (
                f'<iq type="result" id="{xml.get("id")}"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind">'
                f"<jid>{self.bumper_jid}</jid></bind></iq>"
            )

            self.set_state("BIND")
            self.send(res)

        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def _handle_session(self, xml: Element) -> None:
        """Handle session."""
        self.set_state("READY")
        self.send(f'<iq type="result" id="{xml.get("id")}" />')
        # Schedule the ping task and store it
        self.schedule_ping_task = asyncio.create_task(self.schedule_ping(30))

    def _handle_presence(self, xml: Element) -> None:
        if len(xml) and xml[0].tag == "status":
            _LOGGER_CLIENT.debug(f"bot presence {ET.tostring(xml, encoding='utf-8').decode('utf-8')}")
            # Most likely a bot, possibly hello world in text

            # Send dummy return
            self.send(f'<presence to="{self.bumper_jid}"> dummy </presence>')

            # If it is a BOT, send extras
            if self.type == self.BOT:
                # get device info
                self.send(
                    f'<iq type="set" id="14" to="{self.bumper_jid}" from="{XMPPServer.server_id}">'
                    '<query xmlns="com:ctl"><ctl td="GetDeviceInfo"/></query></iq>',
                )

        else:
            _LOGGER_CLIENT.debug(f"client presence - {ET.tostring(xml, encoding='utf-8').decode('utf-8')}")

            if xml.get("type") == "available":
                _LOGGER_CLIENT.debug(f"client presence available - {ET.tostring(xml, encoding='utf-8').decode('utf-8')}")

                # Send dummy return
                self.send(f'<presence to="{self.bumper_jid}"> dummy </presence>')
            elif xml.get("type") == "unavailable":
                _LOGGER_CLIENT.debug(
                    f"client presence unavailable (DISCONNECT) - {ET.tostring(xml, encoding='utf-8').decode('utf-8')}",
                )

                self.set_state("DISCONNECT")
            else:
                # Sometimes the android app sends these
                _LOGGER_CLIENT.debug(f"client presence (UNKNOWN) - {ET.tostring(xml, encoding='utf-8')}")
                # Send dummy return
                self.send(f'<presence to="{self.bumper_jid}"> dummy </presence>')

    def parse_data(self, data: bytes) -> None:
        """Parse data."""
        xml_str: str = data.decode("utf-8")

        if bumper_isc.DEBUG_LOGGING_XMPP_REQUEST is True:
            _LOGGER_CLIENT.info(f"ORIGINAL :: {xml_str}")

        newdata: str | None = None
        if xml_str.startswith("<?xml"):
            # Strip <?xml and add artificial root
            newdata_r = re.sub(r"(<\?xml[^>]+\?>)", "", xml_str)
            newdata = f"<root>{newdata_r}</root>"
        else:
            # Add artificial root
            newdata = f"<root>{xml_str}</root>"

        # try fixing stream when it is not well closed
        if "stream:stream" in newdata and "</stream:stream>" not in newdata:
            # Regular expression pattern to find <stream:stream ... > elements
            matches = re.findall(r"<stream:stream(?![^>]*\/>)[^>]*>", newdata)
            for match in matches:
                # Replace the element with a properly closed version
                newdata = newdata.replace(match, f"{match[:-1]}/>")
        # some messages have only a close stream
        elif "<stream:stream>" not in newdata and "</stream:stream>" in newdata:
            newdata = None
            # Close stream
            _LOGGER_CLIENT.debug(f"Send/Set disconnect by stream - {newdata}")
            self.send("</stream:stream>")
            self.set_state("DISCONNECT")
            return

        if bumper_isc.DEBUG_LOGGING_XMPP_REQUEST_REFACTOR is True:
            _LOGGER_CLIENT.info(f"REFACTOR :: {newdata}")

        try:
            root = ET.fromstring(newdata)
            for item in root.iter():
                item_tag: str = item.tag.split("}")[-1]
                item_namespace: str = item.tag.split("}")[0][1:]

                if item_tag == "root":
                    continue

                if item_tag == "iq":
                    if self.log_incoming_data:
                        _LOGGER_CLIENT.debug(
                            f"from ({self.address[0]}:{self.address[1]} | {self.bumper_jid})"
                            f" - {str(ET.tostring(item, encoding='utf-8').decode('utf-8')).replace('ns0:', '')}",
                        )
                        if 'td="error"' in newdata or "errs=" in newdata or 'k="DeviceAlert' in newdata:
                            _LOGGER_CLIENT.error(
                                f"Received Error from ({self.address[0]}:{self.address[1]} | {self.bumper_jid}) - {newdata}",
                            )
                    self._handle_iq(item, newdata)
                    item.clear()

                elif item_tag == "auth" and item_namespace == "urn:ietf:params:xml:ns:xmpp-sasl":  # SASL Auth
                    self._handle_sasl_auth(item)
                    item.clear()

                elif item_tag == "starttls" and self.tls_upgraded is False:
                    asyncio.Task(self._handle_starttls())
                    item.clear()

                elif item_tag == "presence":
                    self._handle_presence(item)
                    item.clear()

                elif item_tag == "stream" and self.state in (self.CONNECT, self.INIT):
                    _LOGGER_CLIENT.debug(f"Handling connect data - {newdata}")
                    self._handle_connect(newdata)
                    item.clear()

                elif self.log_incoming_data:
                    _LOGGER_CLIENT.warning(
                        f"Unparsed Item - {str(ET.tostring(item, encoding='utf-8').decode('utf-8')).replace('ns0:', '')}",
                    )
                    item.clear()

        except ET.ParseError as e:
            _LOGGER_CLIENT.error(f"xml parse error :: {newdata} :: {e}", exc_info=True)
        except Exception:
            _LOGGER_CLIENT.exception(utils.default_exception_str_builder(), exc_info=True)

    def _handle_iq(self, xml: Element, data: str) -> None:
        child = self._tag_strip_uri(xml[0].tag) if len(xml) else None

        if xml.tag == "iq":
            if child == "bind":
                self._handle_bind(xml)
            elif child == "session":
                self._handle_session(xml)
            elif child == "ping":
                self._handle_ping(xml)
            elif child == "query":
                if self.type == self.BOT:
                    self._handle_result(xml, data)
                else:
                    self._handle_ctl(xml, data)
            elif xml.get("type") == "result" or xml.get("type") == "set":
                self._handle_result(xml, data)

    def _xml_replacer(self, xml: Element, tag: str, xmlns: str) -> str:
        # clean up string to remove namespaces added by ET
        rxmlstring = ET.tostring(xml).decode("utf-8")
        # Replace "xmlns:ns0" with "xmlns"
        rxmlstring = re.sub(r"xmlns:ns0=", "xmlns=", rxmlstring)
        # Remove all namespaces for "ns0:"
        rxmlstring = re.sub(r"ns0:", "", rxmlstring)
        # Inside "iq" element, remove the attribute "xmlns" with {xmlns}
        rxmlstring = re.sub(rf'<iq([^>]*) xmlns=["\']{xmlns}["\']([^>]*)>', r"<iq\1\2>", rxmlstring)
        # Inside "{tag}" element, add 'xmlns="{xmlns}"'
        return re.sub(rf"<{tag}(?! xmlns)([^>]*)>", rf'<{tag} xmlns="{xmlns}"\1>', rxmlstring)

    def to_dict(self) -> dict[str, str | int | tuple[str, int] | None]:
        """Serialize XMPPAsyncClient to a dictionary."""
        return {
            "uid": self.uid,
            "bumper_jid": self.bumper_jid,
            "state": self.state,
            "address": self.address,
            "type": "BOT" if self.type == self.BOT else "CONTROLLER" if self.type == self.CONTROLLER else "UNKNOWN",
        }
