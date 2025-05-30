"""https://github.com/nikitastupin/mitmproxy-mqtt-script."""  # noqa: INP001

from pathlib import Path
import struct
from typing import Any

from mitmproxy import ctx, http, tcp
from mitmproxy.utils import strutils


class MQTTControlPacket:
    """MQTT sniffing."""

    # Packet types
    (
        CONNECT,
        CONNACK,
        PUBLISH,
        PUBACK,
        PUBREC,
        PUBREL,
        PUBCOMP,
        SUBSCRIBE,
        SUBACK,
        UNSUBSCRIBE,
        UNSUBACK,
        PINGREQ,
        PINGRESP,
        DISCONNECT,
    ) = range(1, 15)

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.1_-
    Names = [
        "reserved",
        "CONNECT",
        "CONNACK",
        "PUBLISH",
        "PUBACK",
        "PUBREC",
        "PUBREL",
        "PUBCOMP",
        "SUBSCRIBE",
        "SUBACK",
        "UNSUBSCRIBE",
        "UNSUBACK",
        "PINGREQ",
        "PINGRESP",
        "DISCONNECT",
        "reserved",
    ]

    PACKETS_WITH_IDENTIFIER = [
        PUBACK,
        PUBREC,
        PUBREL,
        PUBCOMP,
        SUBSCRIBE,
        SUBACK,
        UNSUBSCRIBE,
        UNSUBACK,
    ]

    def __init__(self, packet: Any) -> None:
        self._packet = packet
        # Fixed header
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718020
        self.packet_type = self._parse_packet_type()
        self.packet_type_human = self.Names[self.packet_type]
        self.dup, self.qos, self.retain = self._parse_flags()
        self.remaining_length, self.total_length = self._parse_remaining_length()
        if self.total_length > len(packet):
            # Partial packet, raise BlockingIOError (the Python error than best corresponds to errno EAGAIN)
            msg = f"Incomplete MQTT control packet: only {len(packet)} bytes remaining, but header expected {self.total_length}"
            raise BlockingIOError(
                msg,
                len(packet),
            )
        self._packet, self._extra = packet[: self.total_length], packet[self.total_length :]
        # Variable header & Payload
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718024
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718026
        if self.packet_type == self.CONNECT:
            self._parse_connect_variable_headers()
            self._parse_connect_payload()
        elif self.packet_type == self.PUBLISH:
            self._parse_publish_variable_headers()
            self._parse_publish_payload()
        elif self.packet_type == self.SUBSCRIBE:
            self._parse_subscribe_variable_headers()
            self._parse_subscribe_payload()
        elif self.packet_type in (self.SUBACK, self.UNSUBSCRIBE):
            pass
        else:
            self.payload = None

    def pprint(self) -> str:
        """MQTT sniffing."""
        s = f"[{self.Names[self.packet_type]}]"

        if self.packet_type == self.CONNECT:
            s += f"""

Client Id: {self.payload.get("ClientId")}
Will Topic: {self.payload.get("WillTopic")}
Will Message: {strutils.bytes_to_escaped_str(self.payload.get("WillMessage", b"None"))}
User Name: {self.payload.get("UserName")}
Password: {strutils.bytes_to_escaped_str(self.payload.get("Password", b"None"))}
"""
        elif self.packet_type == self.SUBSCRIBE:
            s += " sent topic filters: "
            s += ", ".join([f"'{tf}'" for tf in self.topic_filters])
        elif self.packet_type == self.PUBLISH:
            topic_name = strutils.bytes_to_escaped_str(self.topic_name)
            payload = strutils.bytes_to_escaped_str(self.payload)

            s += f" '{payload}' to topic '{topic_name}'"
        elif self.packet_type in [self.PINGREQ, self.PINGRESP]:
            pass
        else:
            s = f"Packet type {self.Names[self.packet_type]} is not supported yet!"

        return s

    def _parse_length_prefixed_bytes(self, offset: Any) -> tuple[Any, Any]:
        field_length_bytes = self._packet[offset : offset + 2]
        field_length = struct.unpack("!H", field_length_bytes)[0]

        field_content_bytes = self._packet[offset + 2 : offset + 2 + field_length]

        return field_length + 2, field_content_bytes

    def _parse_publish_variable_headers(self) -> None:
        offset = len(self._packet) - self.remaining_length

        field_length, field_content_bytes = self._parse_length_prefixed_bytes(offset)
        self.topic_name = field_content_bytes

        if self.qos in [0x01, 0x02]:
            offset += field_length
            self.packet_identifier = self._packet[offset : offset + 2]

    def _parse_publish_payload(self) -> None:
        fixed_header_length = len(self._packet) - self.remaining_length
        variable_header_length = 2 + len(self.topic_name)

        if self.qos in [0x01, 0x02]:
            variable_header_length += 2

        offset = fixed_header_length + variable_header_length

        self.payload = self._packet[offset:]

    def _parse_subscribe_variable_headers(self) -> None:
        self._parse_packet_identifier()

    def _parse_subscribe_payload(self) -> None:
        offset = len(self._packet) - self.remaining_length + 2

        self.topic_filters = {}

        while len(self._packet) - offset > 0:
            field_length, topic_filter_bytes = self._parse_length_prefixed_bytes(offset)
            offset += field_length

            qos = self._packet[offset : offset + 1]
            offset += 1

            topic_filter = topic_filter_bytes.decode("utf-8")
            self.topic_filters[topic_filter] = {"qos": qos}

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718030
    def _parse_connect_variable_headers(self) -> None:
        offset = len(self._packet) - self.remaining_length

        self.variable_headers = {}
        self.connect_flags = {}

        self.variable_headers["ProtocolName"] = self._packet[offset : offset + 6]
        self.variable_headers["ProtocolLevel"] = self._packet[offset + 6 : offset + 7]
        self.variable_headers["ConnectFlags"] = self._packet[offset + 7 : offset + 8]
        self.variable_headers["KeepAlive"] = self._packet[offset + 8 : offset + 10]
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349229
        if len(self.variable_headers["ConnectFlags"]) > 0:
            self.connect_flags["CleanSession"] = bool(self.variable_headers["ConnectFlags"][0] & 0x02)
            self.connect_flags["Will"] = bool(self.variable_headers["ConnectFlags"][0] & 0x04)
            self.will_qos = (self.variable_headers["ConnectFlags"][0] >> 3) & 0x03
            self.connect_flags["WillRetain"] = bool(self.variable_headers["ConnectFlags"][0] & 0x20)
            self.connect_flags["Password"] = bool(self.variable_headers["ConnectFlags"][0] & 0x40)
            self.connect_flags["UserName"] = bool(self.variable_headers["ConnectFlags"][0] & 0x80)

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718031
    def _parse_connect_payload(self) -> None:
        fields = []
        offset = len(self._packet) - self.remaining_length + 10

        while len(self._packet) - offset > 0:
            field_length, field_content = self._parse_length_prefixed_bytes(offset)
            fields.append(field_content)
            offset += field_length

        self.payload = {}

        for f in fields:
            # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349242
            if "ClientId" not in self.payload:
                self.payload["ClientId"] = f.decode("utf-8")
            # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349243
            elif self.connect_flags["Will"] and "WillTopic" not in self.payload:
                self.payload["WillTopic"] = f.decode("utf-8")
            elif self.connect_flags["Will"] and "WillMessage" not in self.payload:
                self.payload["WillMessage"] = f
            elif self.connect_flags["UserName"] and "UserName" not in self.payload:
                self.payload["UserName"] = f.decode("utf-8")
            elif self.connect_flags["Password"] and "Password" not in self.payload:
                self.payload["Password"] = f
            else:
                msg = ""
                raise Exception(msg)

    def _parse_packet_type(self) -> Any:
        return self._packet[0] >> 4

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718022
    def _parse_flags(self) -> Any:
        dup = None
        qos = None
        retain = None

        if self.packet_type == self.PUBLISH:
            dup = (self._packet[0] >> 3) & 0x01
            qos = (self._packet[0] >> 1) & 0x03
            retain = self._packet[0] & 0x01

        return dup, qos, retain

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.4_Size
    # Returns (remaining, total): latter includes the fixed header
    def _parse_remaining_length(self) -> (int, int):
        multiplier = 1
        value = 0
        i = 1

        while True:
            encoded_byte = self._packet[i]
            value += (encoded_byte & 127) * multiplier
            multiplier *= 128

            if multiplier > 128 * 128 * 128:
                msg = "Malformed Remaining Length"
                raise Exception(msg)

            if encoded_byte & 128 == 0:
                break

            i += 1

        return value, value + i + 1

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.5_-
    def _parse_packet_identifier(self) -> None:
        offset = len(self._packet) - self.remaining_length
        self.packet_identifier = self._packet[offset : offset + 2]


def tcp_message(flow: tcp.TCPFlow | http.HTTPFlow) -> None:
    """MQTT sniffing."""
    message = flow.messages[-1]

    mqtt_packet = MQTTControlPacket(message.content)
    dump(mqtt_packet)


def dump(mqtt_packet: MQTTControlPacket) -> None:
    """MQTT sniffing."""
    # log_message = mqtt_packet.pprint()
    # ctx.log.info(log_message)

    # # This way we can save topics
    with Path("/mitm/mqtt_traffic.txt").open("w", encoding="utf-8") as outfile:
        outfile.write(mqtt_packet.pprint())
    #     if mqtt_packet.packet_type == mqtt_packet.PUBLISH:
    #         outfile.write(f"{mqtt_packet.topic_name}\n")
    #     elif mqtt_packet.packet_type == mqtt_packet.SUBSCRIBE:
    #         outfile.write(f"{mqtt_packet.topic_filters}\n")


# Websocket has a perfectly reasonable mechanism to frame protocols
# layered on top of it (just as TCP does). But Amazon MQTT servers don't use this
# correctly, so MQTT packets get concatenated and split across Webscoket
# messages and need to be reassembled.
ws_buffer: dict[str, bytes] = {}


def websocket_start(flow: http.HTTPFlow) -> None:
    """MQTT sniffing."""
    global ws_buffer  # noqa: PLW0602
    ws_buffer[flow.id] = b""


def websocket_end(flow: http.HTTPFlow) -> None:
    """MQTT sniffing."""
    global ws_buffer  # noqa: PLW0602
    if b := ws_buffer.pop(flow.id):
        ctx.log.warn(f"{len(b)} bytes of partial MQTT packet left on disconnection: {b.hex()}")


def websocket_message(flow: http.HTTPFlow) -> None:
    """MQTT sniffing."""
    global ws_buffer  # noqa: PLW0602
    assert flow.websocket  # noqa: S101
    fid = flow.id

    ws_buffer[fid] += flow.websocket.messages[-1].content
    while ws_buffer[fid]:
        try:
            mqtt_packet = MQTTControlPacket(ws_buffer[fid])
        except BlockingIOError:
            ctx.log.debug("Awaiting more bytes for complete MQTT control packet")
            break
        else:
            dump(mqtt_packet)
            b = ws_buffer[fid] = mqtt_packet._extra  # noqa: SLF001
            if b:
                ctx.log.debug(f"Saving remaining {len(b)} bytes after MQTT control packet")
