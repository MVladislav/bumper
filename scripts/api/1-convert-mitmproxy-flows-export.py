#!/usr/bin/env python3
"""
Convert an exported mitmproxy flow file into a readable transcript.

Reads a mitmproxy flow file (the binary tnetstring format written by
mitmdump/mitmweb with "-w file") and writes a smaller, cleaner copy:

  * TLS certificate chains are dropped by default. In a typical app capture they
    are about 30% of the file and say nothing about the proxied conversation.
  * Secrets in headers, query strings and JSON/form bodies are replaced with
    "<redacted>" by default, so the result can be handed to an AI or pasted
    into a bug report without leaking tokens. Use "--no-redact" to disable.
  * Flows can be filtered by host, path, method, status, content type, flow
    type or error state, so only the interesting conversation is left.
  * Request/response bodies can be dropped ("--drop-content") or truncated
    ("--max-body").
  * Streamed TCP traffic is decoded where the protocol is recognizable: MQTT
    packets are shown as CONNECT/PUBLISH/SUBSCRIBE with topic and payload, and
    text protocols (XMPP, IMAP, IRC, ...) are shown as text instead of hex.
    MQTT auto-detection uses the CONNECT packet as well as standard ports, so
    MQTT carried over TLS on port 443 is recognized.
  * MQTT messages and text/JSON payloads are complete by default. Opaque binary
    payloads can be included in full with `--full-binary --no-redact`.

Output formats:

  text    (default) readable transcript, one block per flow, for humans and AI
  json              machine readable list of flows
  mitm              binary flow file, still loadable in mitmweb/mitmdump
  stats             inventory of the capture, to pick filters with

Secrets are redacted when rendering. In the "mitm" output the raw stream bytes
are left untouched, because rewriting them would corrupt the protocol; share
the text or json output when a capture contains streamed protocols.

The result is written to `data/flows/` by default, named after the input:
`capture.mitm` becomes `data/flows/capture-clean`. `-o` chooses another file,
and `-o -` writes to stdout. The directory is local working data and is not
committed. The summary line goes to stderr.

Requirements: python3 (standard library only)

Usage:
  1-convert-mitmproxy-flows-export.py [options] <flow-file> [-o <out>]
  1-convert-mitmproxy-flows-export.py [options] <flow-file> -f stats

Examples:
  # transcript of one host, secrets redacted
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm --host '*.example.com'

  # what is in the capture, before choosing filters
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm -f stats

  # failing requests only, bodies capped at 4 KiB, secrets left untouched
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm --only-errors --max-body 4096 --no-redact

  # smaller capture that mitmweb can still open
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm -f mitm --drop-content -o clean.mitm

  # MQTT only, decoded packets, as JSON
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm --flow-type tcp --decode mqtt -f json

  # include opaque binary MQTT payloads in the local transcript
  scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm --flow-type tcp --full-binary --no-redact
"""

import argparse
import base64
import fnmatch
import gzip
import json
from pathlib import Path
import re
import sys
import zlib
from collections import Counter
from datetime import datetime
from datetime import timezone

TOOL = "1-convert-mitmproxy-flows-export"
VERSION = "1.3.0"
PLACEHOLDER = "<redacted>"

#: The repository, so the default output directory does not depend on the cwd.
REPO_ROOT = Path(__file__).parents[2]
#: Local working data; the transcripts are not committed.
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/flows"
#: Suffixes that an exported flow file can carry.
FLOW_SUFFIXES = (".mitm", ".flow", ".tnetstring", ".har", ".json")

# Header/parameter names whose value is treated as a secret. Names are matched
# as a substring of the normalized name (lower case, non alphanumeric removed),
# so "X-CA-Signature", "authSign" and "access_token" match "signature",
# "authsign" and "accesstoken".
DEFAULT_SECRET_NAMES = [
    "authorization",
    "proxyauthorization",
    "cookie",
    "setcookie",
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "xapikey",
    "accesskey",
    "privatekey",
    "sessionid",
    "jsessionid",
    "phpsessid",
    "authsign",
    "authappkey",
    "authtoken",
    "authkey",
    "authsecret",
    "sign",
    "signature",
    "jwt",
    "bearer",
    "credential",
    "passphrase",
]

# Transport headers hidden in text output by default: they describe the
# connection, not the conversation.
NOISE_HEADERS = {
    "acceptencoding",
    "contentlength",
    "contentencoding",
    "date",
    "server",
    "connection",
    "keepalive",
    "transferencoding",
    "etag",
    "lastmodified",
    "acceptranges",
    "ifmodifiedsince",
    "ifnonematch",
    "vary",
    "allow",
    "p3p",
    "xpoweredby",
    "reportto",
    "nel",
    "altsvc",
}

STATUS_GROUPS = {
    "1xx": range(100, 200),
    "2xx": range(200, 300),
    "3xx": range(300, 400),
    "4xx": range(400, 500),
    "5xx": range(500, 600),
}


# *** Error handling ***


def exit_with_error(message):
    """Print a fatal error to stderr and exit with status 1."""
    sys.stderr.write(f"{TOOL}: ERROR: {message}\n")
    raise SystemExit(1)


# *** Tnetstring codec ***
# mitmproxy variant: <byte-length>:<data><type> where the type tag is
# ~ null, ! bool, # int, ^ float, , bytes, ; str, ] list, } dict


def tns_parse(kind, data):
    """Decode one tnetstring payload of the given type tag."""
    if kind == b",":
        return bytes(data)
    if kind == b";":
        return data.decode("utf-8", "replace")
    if kind == b"#":
        return int(data)
    if kind == b"^":
        return float(data)
    if kind == b"!":
        return data == b"true"
    if kind == b"~":
        return None
    if kind == b"]":
        items = []
        while data:
            item, data = tns_pop(data)
            items.append(item)
        return items
    if kind == b"}":
        out = {}
        while data:
            key, data = tns_pop(data)
            value, data = tns_pop(data)
            out[key] = value
        return out
    raise ValueError("unknown tnetstring type tag: %r" % kind)


def tns_pop(data):
    """Pop one tnetstring off the front of data. Returns (value, rest)."""
    index = data.find(b":")
    if index < 0:
        raise ValueError("not a tnetstring: missing length prefix")
    try:
        length = int(data[:index])
    except ValueError:
        raise ValueError("not a tnetstring: invalid length prefix")
    body = data[index + 1 :]
    if len(body) < length + 1:
        raise ValueError("truncated payload")
    return tns_parse(body[length : length + 1], body[:length]), body[length + 1 :]


def tns_dumps(value):
    """Serialize a value byte compatible with mitmproxy.io.tnetstring.dumps."""
    if value is None:
        return b"0:~"
    if value is True:
        return b"4:true!"
    if value is False:
        return b"5:false!"
    if isinstance(value, int):
        data = str(value).encode()
        kind = b"#"
    elif isinstance(value, float):
        data = repr(value).encode()
        kind = b"^"
    elif isinstance(value, (bytes, bytearray)):
        data = bytes(value)
        kind = b","
    elif isinstance(value, str):
        data = value.encode("utf-8")
        kind = b";"
    elif isinstance(value, (list, tuple)):
        payload = b"".join(tns_dumps(item) for item in value)
        return b"%d:%s]" % (len(payload), payload)
    elif isinstance(value, dict):
        payload = b"".join(tns_dumps(key) + tns_dumps(item) for key, item in value.items())
        return b"%d:%s}" % (len(payload), payload)
    else:
        raise ValueError("unserializable value: %s" % type(value).__name__)
    return b"%d:%s%s" % (len(data), data, kind)


def load_flows(raw):
    """Parse a whole flow file into a list of flow state dicts."""
    flows = []
    rest = raw
    while rest:
        try:
            flow, rest = tns_pop(rest)
        except ValueError as err:
            raise ValueError("flow %d: %s" % (len(flows) + 1, err))
        if not isinstance(flow, dict):
            raise ValueError("flow %d: expected a dict, got %s" % (len(flows) + 1, type(flow).__name__))
        flows.append(flow)
    return flows


# *** Flow model helpers ***


def as_text(value):
    """Return a flow value as text; older flow files use bytes for these."""
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


def like_original(value, template):
    """Return value typed like template, so flow field types stay unchanged."""
    if isinstance(template, (bytes, bytearray)):
        return value.encode("utf-8") if isinstance(value, str) else value
    return value.decode("utf-8", "replace") if isinstance(value, (bytes, bytearray)) else value


def normalize_name(name):
    """Lower case name without punctuation, for robust secret matching."""
    return re.sub(r"[^a-z0-9]", "", as_text(name).lower())


def header_pairs(message):
    """Return the headers of a request/response state as [name, value] pairs."""
    if not isinstance(message, dict):
        return []
    headers = message.get("headers")
    if not isinstance(headers, list):
        return []
    return [pair for pair in headers if isinstance(pair, list) and len(pair) == 2]


def header_value(message, wanted):
    """Return the first value of header 'wanted' as text, '' when absent."""
    target = normalize_name(wanted)
    for name, value in header_pairs(message):
        if normalize_name(name) == target:
            return as_text(value)
    return ""


def set_header(message, wanted, text):
    """Set a header value, keeping the original value type."""
    target = normalize_name(wanted)
    for pair in header_pairs(message):
        if normalize_name(pair[0]) == target:
            pair[1] = like_original(text, pair[1])
            return


def flow_host(flow):
    """Host of a flow, request host first, authority as fallback."""
    request = flow.get("request") or {}
    return as_text(request.get("host")) or as_text(request.get("authority"))


def flow_url(flow):
    """Absolute URL of a flow request."""
    request = flow.get("request") or {}
    host = flow_host(flow)
    port = request.get("port")
    scheme = as_text(request.get("scheme")) or "http"
    path = as_text(request.get("path")) or "/"
    if port is None or (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        netloc = host
    else:
        netloc = f"{host}:{port}"
    return f"{scheme}://{netloc}{path}"


def flow_status(flow):
    """Status code of a flow response, None when there is no response."""
    response = flow.get("response")
    return response.get("status_code") if isinstance(response, dict) else None


def flow_timestamp(flow):
    """Best available timestamp of a flow."""
    for source in (flow.get("response"), flow.get("request")):
        if isinstance(source, dict) and source.get("timestamp_start"):
            return source["timestamp_start"]
    return flow.get("timestamp_created")


def stream_messages(flow):
    """Streamed messages of a tcp/udp flow or of a websocket handshake."""
    for key in ("messages", "websocket"):
        messages = flow.get(key)
        if isinstance(messages, list) and messages:
            return messages
    return []


def connection_summary(flow):
    """One line about the server connection, used for non-HTTP flows."""
    conn = flow.get("server_conn") or {}
    address = conn.get("address") or []
    peer = f"{address[0]}:{address[1]}" if len(address) > 1 else "(unknown)"
    parts = [peer]
    if conn.get("tls_version"):
        parts.append("TLS %s" % as_text(conn.get("tls_version")))
    if conn.get("alpn"):
        parts.append("alpn %s" % as_text(conn.get("alpn")))
    if conn.get("cipher"):
        parts.append(as_text(conn.get("cipher")))
    error = conn.get("error")
    if error:
        parts.append("error: %s" % as_text(error))
    return "server connection: %s" % ", ".join(parts)


def is_error_flow(flow):
    """A flow is an error flow when mitmproxy or the server reported failure."""
    if flow.get("error"):
        return True
    status = flow_status(flow)
    return status is None or status >= 400


def format_time(value):
    """Format a unix timestamp as UTC with millisecond precision."""
    if not isinstance(value, (int, float)):
        return "-"
    stamp = datetime.fromtimestamp(value, timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (stamp.microsecond // 1000)


def human_size(count):
    """Format a byte count for humans."""
    size = float(count)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "%d B" % count


# *** Body helpers ***


def decode_body(content):
    """Decode gzip/deflate bodies so the transcript shows plain text."""
    content, _ = decode_body_ex(content)
    return content


def decode_body_ex(content):
    """Decode a body. Returns (decoded bytes, encoding name or None)."""
    if not content or len(content) < 2:
        return content, None
    if content[:2] == b"\x1f\x8b":
        openers = (
            ("gzip", gzip.decompress),
            ("gzip", lambda data: zlib.decompress(data, 16 + zlib.MAX_WBITS)),
            ("gzip", zlib.decompress),
        )
    else:
        openers = (("deflate", lambda data: zlib.decompress(data, 16 + zlib.MAX_WBITS)), ("deflate", zlib.decompress))
    for name, opener in openers:
        try:
            return opener(content), name
        except (OSError, zlib.error):
            continue
    return content, None


def encode_body(content, encoding):
    """Re-apply a content encoding after a body was rewritten."""
    if encoding == "gzip":
        return gzip.compress(content)
    if encoding == "deflate":
        return zlib.compress(content)
    return content


def decode_text(content):
    """Return content as text, or None when it is not printable text."""
    if not content:
        return ""
    if b"\x00" in content[:4096]:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def set_content(message, content):
    """Replace a body, keeping its type and the content-length header correct."""
    message["content"] = like_original(content, message.get("content"))
    set_header(message, "content-length", str(len(message["content"])))


# *** Stream protocol decoding ***
# mitmproxy hands over streamed TCP traffic as raw bytes. Text protocols need no
# help, binary ones (MQTT) are only readable when decoded.


MQTT_TYPES = {
    1: "CONNECT",
    2: "CONNACK",
    3: "PUBLISH",
    4: "PUBACK",
    5: "PUBREC",
    6: "PUBREL",
    7: "PUBCOMP",
    8: "SUBSCRIBE",
    9: "SUBACK",
    10: "UNSUBSCRIBE",
    11: "UNSUBACK",
    12: "PINGREQ",
    13: "PINGRESP",
    14: "DISCONNECT",
    15: "AUTH",
}

MQTT_PORTS = (1883, 1884, 8883, 9001, 15675, 25672)

DEFAULT_PREVIEW = {"preview": "hex"}

CONNECT_FLAGS = [
    (0x80, "reserved"),
    (0x40, "clean session"),
    (0x20, "will flag"),
    (0x18, "will qos"),
    (0x04, "will retain"),
    (0x02, "password"),
    (0x01, "username"),
]


def looks_like_mqtt(messages):
    """Detect MQTT packets in a stream by its CONNECT signature or ports."""
    if not messages:
        return False
    for message in messages:
        if not (isinstance(message, list) and len(message) == 3):
            continue
        data = message[1] or b""
        if len(data) < 4 or data[0] >> 4 != 1:
            continue
        remaining_length, body_start = mqtt_varint(data, 1)
        if remaining_length is None or body_start + 2 > len(data):
            continue
        protocol_length = (data[body_start] << 8) | data[body_start + 1]
        protocol_end = body_start + 2 + protocol_length
        if (
            protocol_length in (4, 6)
            and protocol_end <= len(data)
            and data[body_start + 2 : protocol_end] in (b"MQTT", b"MQIsdp")
        ):
            return True
    return False


def flow_server_port(flow):
    address = (flow.get("server_conn") or {}).get("address") or []
    return address[1] if len(address) > 1 else None


def stream_decoder_for(flow, opts):
    """Pick the stream decoder for a flow. Returns (protocol name, function)."""
    if opts.decode == "off":
        return "raw", None
    if opts.decode != "auto":
        return opts.decode, STREAM_DECODERS.get(opts.decode)
    messages = stream_messages(flow)
    if looks_like_mqtt(messages) or flow_server_port(flow) in MQTT_PORTS:
        return "mqtt", STREAM_DECODERS["mqtt"]
    return "raw", None


def mqtt_varint(data, pos):
    """Read an MQTT variable byte integer. Returns (value, next position)."""
    value = 0
    multiplier = 1
    for _ in range(4):
        if pos >= len(data):
            return None, pos
        byte = data[pos]
        pos += 1
        value += (byte & 0x7F) * multiplier
        if not byte & 0x80:
            return value, pos
        multiplier *= 128
    return None, pos


def mqtt_string(data, pos):
    """Read a length prefixed MQTT UTF-8 string. Returns (value, next pos)."""
    raw, pos = mqtt_binary(data, pos)
    return raw.decode("utf-8", "replace"), pos


def mqtt_binary(data, pos):
    """Read a two byte length prefixed MQTT binary field. Returns (bytes, pos)."""
    if pos + 2 > len(data):
        return b"", pos
    length = (data[pos] << 8) | data[pos + 1]
    pos += 2
    return bytes(data[pos : pos + length]), pos + length


def decode_mqtt(data, opts, redactor):
    """Decode all MQTT control packets in one streamed message.

    Returns a list of lines. Payloads are shown as text, JSON payloads are
    pretty printed and redacted, everything else is previewed as hex/base64.
    A message that does not parse as MQTT is rendered as raw payload, so a
    wrong or forced "--decode mqtt" cannot turn text into nonsense.
    """
    lines = []
    pos = 0
    while pos < len(data):
        header = data[pos]
        kind = header >> 4
        flags = header & 0x0F
        length, body_start = mqtt_varint(data, pos + 1)
        if kind not in MQTT_TYPES or length is None or body_start + length > len(data):
            return render_stream_payload(data, opts, redactor)
        body = data[body_start : body_start + length]
        packet_lines = render_mqtt_packet(kind, flags, body, opts, redactor)
        if packet_lines is None:
            return render_stream_payload(data, opts, redactor)
        lines.extend(packet_lines)
        pos = body_start + length
    if pos != len(data):
        lines.append("trailing %d bytes: %s" % (len(data) - pos, preview_bytes(data[pos : pos + 24], opts)))
    return lines


def render_mqtt_packet(kind, flags, body, opts, redactor):
    """Render one decoded MQTT packet as text lines, None when it is not MQTT."""
    name = MQTT_TYPES[kind]
    lines = []
    pos = 0
    if kind == 1:
        protocol, _ = mqtt_string(body, 0)
        if protocol not in ("MQTT", "MQIsdp"):
            return None
        return render_mqtt_connect(body, opts, redactor)
    if kind in (12, 13) and body:
        return None
    if kind == 2:
        code = body[1] if len(body) > 1 else None
        return [f"CONNACK session present {bool(flags & 1)}, return code {MQTT_CONNACK.get(code, code)}"]
    if kind == 3:
        topic, pos = mqtt_string(body, pos)
        qos = (flags & 0x06) >> 1
        head = "PUBLISH qos %d%s" % (qos, ", retained" if flags & 1 else "")
        if qos:
            packet_id = (body[pos] << 8) | body[pos + 1] if len(body) > pos + 1 else None
            pos += 2
            head += ", packet id %s" % packet_id
        lines = ["%s topic %s (%d bytes payload)" % (head, topic, max(0, len(body) - pos))]
        lines.extend(render_stream_payload(body[pos:], opts, redactor, default_limit=0))
        return lines
    if kind in (8, 10):
        packet_id = (body[0] << 8) | body[1] if len(body) > 1 else None
        pos = 2
        topics = []
        while pos < len(body):
            topic, pos = mqtt_string(body, pos)
            qos = body[pos] if pos < len(body) else 0
            pos += 1
            topics.append("%s (qos %d)" % (topic, qos))
        head = "%s packet id %s, %d topic filter(s)" % (name, packet_id, len(topics))
        return [head] + ["  %s" % topic for topic in topics[: opts.max_topics]]
    if kind in (4, 5, 6, 7, 9, 11):
        packet_id = (body[0] << 8) | body[1] if len(body) > 1 else None
        codes = [str(byte) for byte in body[2:]]
        head = f"{name} packet id {packet_id}"
        if codes:
            head += ", codes %s" % ", ".join(codes)
        return [head]
    return [name]


MQTT_CONNACK = {
    0: "accepted",
    1: "unacceptable protocol version",
    2: "identifier rejected",
    3: "server unavailable",
    4: "bad user name or password",
    5: "not authorized",
}


def render_mqtt_connect(body, opts, redactor):
    """Render a CONNECT packet with its client id, will topic and credentials."""
    lines = []
    name, pos = mqtt_string(body, 0)
    level = body[pos] if len(body) > pos else 0
    flags = body[pos + 1] if len(body) > pos + 1 else 0
    keepalive = ((body[pos + 2] << 8) | body[pos + 3]) if len(body) > pos + 3 else 0
    pos += 4
    options = [label for bit, label in CONNECT_FLAGS if flags & bit and label != "reserved"]
    version = {3: "v3.1", 4: "v3.1.1", 5: "v5"}.get(level, "level %s" % level)
    lines.append("CONNECT %s, keepalive %ds%s" % (version, keepalive, ", " + ", ".join(options) if options else ""))
    if level == 5:
        properties, pos = mqtt_varint(body, pos)
        pos += properties or 0
    client_id, pos = mqtt_string(body, pos)
    lines.append("  client id: %s" % client_id)
    if flags & 0x20:
        if level == 5:
            will_properties, pos = mqtt_varint(body, pos)
            pos += will_properties or 0
        will_topic, pos = mqtt_string(body, pos)
        will_message, pos = mqtt_binary(body, pos)
        lines.append("  will: %s (qos %d%s)" % (will_topic, (flags & 0x18) >> 3, ", retained" if flags & 0x04 else ""))
        lines.extend(render_stream_payload(will_message, opts, redactor, prefix="    ", default_limit=0))
    if flags & 0x02:
        username, pos = mqtt_binary(body, pos)
        lines.append("  username: %s" % redact_text(username, "username", redactor, opts))
    if flags & 0x04:
        password, pos = mqtt_binary(body, pos)
        lines.append("  password: %s" % redact_text(password, "password", redactor, opts))
    lines.extend(render_mqtt_undeclared(body, pos, redactor))
    return lines


def render_mqtt_undeclared(body, pos, redactor):
    """Show CONNECT payload fields the flags did not announce.

    Some SDKs append a username and a password hash although the connect flags
    say there are none; those fields carry credentials, so hex looking values
    are redacted instead of being printed.
    """
    lines = []
    index = 0
    while pos + 2 <= len(body):
        field, pos = mqtt_binary(body, pos)
        index += 1
        if not field:
            continue
        if redactor.enabled and looks_like_credential(field):
            redactor.hits["mqttfield%d" % index] += 1
            lines.append(
                "  undeclared field %d: %s (%d bytes, redacted)" % (index, "hex" if is_hex(field) else "opaque", len(field))
            )
        else:
            lines.append("  undeclared field %d: %s" % (index, field.decode("utf-8", "replace")))
    if pos < len(body):
        lines.append("  trailing %d unparsed bytes: %s" % (len(body) - pos, preview_bytes(body[pos : pos + 24], DEFAULT_PREVIEW)))
    return lines


def is_hex(data):
    """True when the bytes are only hex digits, i.e. a hash or id."""
    return bool(data) and all(byte in b"0123456789abcdefABCDEF" for byte in data)


def looks_like_credential(data):
    """True for values that look like a hash, token or key material."""
    if len(data) < 16:
        return False
    return is_hex(data) or b"=" in data or len(data) >= 32


def redact_text(value, name, redactor, opts):
    """Redact a protocol string field by name, when redaction is enabled."""
    if redactor.enabled and redactor.is_secret_param(name, value):
        redactor.hits[normalize_name(name)] += 1
        return PLACEHOLDER
    return value.decode("utf-8", "replace")


def preview_bytes(data, opts):
    """Render raw bytes as hex or base64, depending on --preview."""
    data = bytes(data)
    if opts.preview == "base64":
        return base64.b64encode(data).decode("ascii")
    return data.hex(" ")


def is_texty(data):
    """True when most bytes are printable, i.e. a text based protocol."""
    if not data:
        return False
    sample = data[:512]
    printable = sum(1 for byte in sample if 32 <= byte < 127 or byte in (9, 10, 13))
    return printable >= len(sample) * 0.9


STREAM_DECODERS = {"mqtt": decode_mqtt}


def render_stream_payload(data, opts, redactor, prefix="", default_limit=2048):
    """Render one streamed payload as text, redacted JSON, or a preview."""
    if not data:
        return []
    if opts.max_body:
        limit = opts.max_body
    elif opts.max_stream_payload is not None:
        limit = opts.max_stream_payload
    else:
        limit = default_limit
    note = None
    if limit and len(data) > limit:
        note = "%s... %d more bytes" % (prefix, len(data) - limit)
        data = bytes(data[:limit])
    text = decode_text(data)
    lines = []
    if text is not None and is_texty(data):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if parsed is not None:
            redactor.redact_json(parsed)
            text = json.dumps(parsed, indent=2, ensure_ascii=False)
        lines.extend(prefix + line for line in text.rstrip("\n").splitlines())
    else:
        if opts.full_binary:
            encoded = preview_bytes(data, opts)
            lines.append("%s<binary payload %d bytes, %s>" % (prefix, len(data), opts.preview))
            lines.extend(prefix + "  " + encoded[offset : offset + 96] for offset in range(0, len(encoded), 96))
        else:
            lines.append("%s<binary %d bytes: %s>" % (prefix, len(data), preview_bytes(data[:48], opts)))
            if len(data) > 48:
                lines.append(prefix + "  ... use --full-binary --no-redact to include all bytes")
    if note:
        lines.append(note)
    return lines


# *** Redaction ***


class Redactor:
    """Replaces secret values in headers, query strings and JSON/form bodies."""

    def __init__(self, enabled, header_names, param_names, keep_headers, keep_params, value_patterns):
        self.enabled = enabled
        self.header_names = self._names(DEFAULT_SECRET_NAMES, header_names)
        self.param_names = self._names(DEFAULT_SECRET_NAMES, param_names)
        self.keep_headers = self._names([], keep_headers)
        self.keep_params = self._names([], keep_params)
        self.value_patterns = [re.compile(pattern) for pattern in value_patterns]
        self.query_re = re.compile(rb"([^&=?#\s]+)=([^&#]*)")
        self.hits = Counter()
        self.reformatted = 0

    @staticmethod
    def _names(base, extra):
        names = list(base)
        names.extend(normalize_name(name) for name in extra)
        return [name for name in names if name]

    def _is_secret(self, name, value, names, keep):
        if keep:
            for allowed in keep:
                if allowed in normalize_name(name):
                    return False
        flat = normalize_name(name)
        if any(pattern in flat for pattern in names):
            return True
        text = as_text(value)
        return any(pattern.search(text) for pattern in self.value_patterns)

    def is_secret_header(self, name, value):
        return self._is_secret(name, value, self.header_names, self.keep_headers)

    def is_secret_param(self, name, value):
        return self._is_secret(name, value, self.param_names, self.keep_params)

    def redact_headers(self, message):
        """Redact secret header values in place. Returns the hit count."""
        if not self.enabled or not isinstance(message, dict):
            return 0
        hits = 0
        for pair in header_pairs(message):
            name, value = pair
            if not value:
                continue
            if self.is_secret_header(name, value):
                self.hits[normalize_name(name) or "header"] += 1
                pair[1] = like_original(PLACEHOLDER, value)
                hits += 1
        return hits

    def redact_query(self, raw):
        """Redact secret query/form parameters, preserving the formatting."""
        if not self.enabled or not raw:
            return raw
        as_bytes = isinstance(raw, (bytes, bytearray))
        data = bytes(raw) if as_bytes else as_text(raw).encode("utf-8")
        hits = [0]

        def replace(match):
            name = match.group(1).decode("utf-8", "replace")
            value = match.group(2).decode("utf-8", "replace")
            if self.is_secret_param(name, value):
                self.hits[normalize_name(name) or "param"] += 1
                hits[0] += 1
                return match.group(1) + b"=" + PLACEHOLDER.encode("utf-8")
            return match.group(0)

        result = self.query_re.sub(replace, data)
        if as_bytes:
            return result
        return result.decode("utf-8", "replace")

    def redact_body(self, message):
        """Redact a request/response body in place. Returns the hit count."""
        if not self.enabled or not isinstance(message, dict):
            return 0
        content = message.get("content")
        if not content:
            return 0
        content_type = header_value(message, "content-type").lower()
        if "json" in content_type:
            return self._redact_json(message, content)
        if "x-www-form-urlencoded" in content_type:
            return self._redact_form(message, content)
        return 0

    def _redact_json(self, message, content):
        decoded, encoding = decode_body_ex(content)
        text = decode_text(decoded)
        if text is None:
            return 0
        try:
            parsed = json.loads(text)
        except ValueError:
            return 0
        hits = self.redact_json(parsed)
        if not hits:
            return 0
        plain = json.dumps(parsed, indent=2, ensure_ascii=False).encode("utf-8")
        set_content(message, encode_body(plain, encoding))
        self.reformatted += 1
        return hits

    def _redact_form(self, message, content):
        hits = [0]

        def replace(match):
            name = match.group(1).decode("utf-8", "replace")
            value = match.group(2).decode("utf-8", "replace")
            if self.is_secret_param(name, value):
                self.hits[normalize_name(name) or "param"] += 1
                hits[0] += 1
                return match.group(1) + b"=" + PLACEHOLDER.encode("utf-8")
            return match.group(0)

        decoded, encoding = decode_body_ex(content)
        result = self.query_re.sub(replace, bytes(decoded))
        if not hits[0]:
            return 0
        set_content(message, encode_body(result, encoding))
        return hits[0]

    def redact_json(self, node):
        """Replace secret values inside a parsed JSON document, in place."""
        hits = 0
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    hits += self.redact_json(value)
                elif self.is_secret_param(key, value):
                    node[key] = PLACEHOLDER
                    self.hits[normalize_name(key) or "jsonkey"] += 1
                    hits += 1
                else:
                    hits += self.redact_json(value)
        elif isinstance(node, list):
            for item in node:
                hits += self.redact_json(item)
        return hits


# *** Filters ***


def split_list(values):
    """Split comma separated option values into an upper case set."""
    out = set()
    for value in values:
        out.update(part.strip().upper() for part in value.split(",") if part.strip())
    return out


def parse_status_filter(values):
    """Turn status option values into lists of matching status codes."""
    groups = []
    for value in values:
        for part in value.split(","):
            part = part.strip().lower()
            if not part:
                continue
            if part in STATUS_GROUPS:
                groups.append(STATUS_GROUPS[part])
            elif part.isdigit():
                groups.append([int(part)])
            else:
                exit_with_error("invalid status filter: '%s' (use 200, 4xx, ...)" % part)
    return groups


class FlowFilter:
    """Keeps only the flows matching every configured criterion."""

    def __init__(self, opts):
        self.hosts = [host.lower() for host in opts.host]
        self.exclude_hosts = [host.lower() for host in opts.exclude_host]
        self.paths = [path.lower() for path in opts.path]
        self.path_regex = re.compile(opts.path_regex, re.IGNORECASE) if opts.path_regex else None
        self.methods = split_list(opts.method)
        self.statuses = parse_status_filter(opts.status)
        self.content_types = [value.lower() for value in opts.content_type]
        self.flow_types = {item.lower() for item in split_list(opts.flow_type)}
        self.only_errors = opts.only_errors
        self.skip_errors = opts.skip_errors

    def matches(self, flow):
        request = flow.get("request") or {}
        host = flow_host(flow).lower()
        path = as_text(request.get("path"))
        method = as_text(request.get("method")).upper()

        if self.hosts and not any(fnmatch.fnmatch(host, item) for item in self.hosts):
            return False
        if self.exclude_hosts and any(fnmatch.fnmatch(host, item) for item in self.exclude_hosts):
            return False
        if self.paths and not any(needle in path.lower() for needle in self.paths):
            return False
        if self.path_regex and not self.path_regex.search(path):
            return False
        if self.methods and method not in self.methods:
            return False
        if self.flow_types and as_text(flow.get("type")).lower() not in self.flow_types:
            return False
        if self.statuses:
            status = flow_status(flow)
            if status is None or not any(status in group for group in self.statuses):
                return False
        if self.only_errors and not is_error_flow(flow):
            return False
        if self.skip_errors and is_error_flow(flow):
            return False
        if self.content_types:
            found = [
                header_value(request, "content-type").lower(),
                header_value(flow.get("response") or {}, "content-type").lower(),
            ]
            wanted = [*self.content_types]
            if not any(fnmatch.fnmatch(value, pattern) for value in found if value for pattern in wanted):
                return False
        return True


# *** Cleaning ***


class Cleaner:
    """Removes capture noise and applies redaction to one flow."""

    def __init__(self, opts, redactor, stats):
        self.opts = opts
        self.redactor = redactor
        self.stats = stats

    def clean(self, flow):
        """Clean one flow in place, keeping the flow file loadable."""
        self._clean_connections(flow)
        if flow.get("backup") is not None:
            flow["backup"] = None
            self.stats["backup"] += 1
        for key in ("request", "response"):
            message = flow.get(key)
            if isinstance(message, dict):
                self._clean_message(message)
        self._clean_messages(flow)

    def _clean_connections(self, flow):
        """Blank the connection fields that never carry request information.

        The keys are kept and only their values replaced: mitmproxy restores
        connections with a strict state schema and would reject missing keys.
        """
        for side in ("client_conn", "server_conn"):
            conn = flow.get(side)
            if not isinstance(conn, dict):
                continue
            if not self.opts.keep_certs:
                certs = conn.get("certificate_list")
                if certs:
                    self.stats["certs"] += len(certs)
                    self.stats["certs_bytes"] += len(tns_dumps(certs))
                    conn["certificate_list"] = []
                if conn.get("mitmcert") is not None:
                    conn["mitmcert"] = None
            if not self.opts.keep_tls:
                if conn.get("cipher_list"):
                    self.stats["tls_fields"] += 1
                    conn["cipher_list"] = []
                if conn.get("alpn_offers"):
                    conn["alpn_offers"] = []

    def _clean_message(self, message):
        """Redact and shrink one request/response."""
        self.redactor.redact_headers(message)
        self.redactor.redact_body(message)
        path = message.get("path")
        if path:
            message["path"] = like_original(self.redactor.redact_query(path), path)

        content = message.get("content")
        if not content:
            return
        if self.opts.drop_content:
            self.stats["body_bytes"] += len(content)
            self.stats["bodies_truncated"] += 1
            set_content(message, like_original("", content))
            return
        if self.opts.max_body and len(content) > self.opts.max_body:
            self.stats["body_bytes"] += len(content) - self.opts.max_body
            self.stats["bodies_truncated"] += 1
            marker = "\n... [truncated %d of %d bytes]" % (len(content) - self.opts.max_body, len(content))
            kept = bytes(content[: self.opts.max_body]) + like_original(marker, content)
            set_content(message, kept)

    def _clean_messages(self, flow):
        """Truncate streamed messages of websocket/tcp flows."""
        if not stream_messages(flow):
            return
        self.stats["streams"] += 1
        if not self.opts.max_body:
            return
        for message in stream_messages(flow):
            if not (isinstance(message, list) and len(message) == 3):
                continue
            content = message[1]
            if isinstance(content, (bytes, bytearray)) and len(content) > self.opts.max_body:
                self.stats["body_bytes"] += len(content) - self.opts.max_body
                marker = "\n... [truncated %d bytes]" % (len(content) - self.opts.max_body)
                message[1] = bytes(content[: self.opts.max_body]) + marker.encode("utf-8")


# *** Renderers ***


def render_mitm(flows, opts, stats):
    """Binary flow file that mitmproxy can still read."""
    return b"".join(tns_dumps(flow) for flow in flows)


def render_json(flows, opts, stats):
    """Machine readable list of flows."""
    out = []
    for index, flow in enumerate(flows, 1):
        request = flow.get("request")
        response = flow.get("response")
        entry = {
            "index": index,
            "id": as_text(flow.get("id")),
            "type": as_text(flow.get("type")),
            "timestamp": format_time(flow_timestamp(flow)),
            "error": as_text((flow.get("error") or {}).get("msg")),
        }
        if not isinstance(request, dict):
            entry["server"] = connection_summary(flow).replace("server connection: ", "")
        else:
            entry["request"] = {
                "method": as_text(request.get("method")),
                "url": flow_url(flow),
                "http_version": as_text(request.get("http_version")),
                "headers": {as_text(name): as_text(value) for name, value in header_pairs(request)},
                "body_size": len(request.get("content") or b""),
                "body": body_as_text(request),
            }
        if isinstance(response, dict):
            start = request.get("timestamp_start") or 0
            end = response.get("timestamp_end") or 0
            entry["response"] = {
                "status_code": response.get("status_code"),
                "reason": as_text(response.get("reason")),
                "http_version": as_text(response.get("http_version")),
                "headers": {as_text(name): as_text(value) for name, value in header_pairs(response)},
                "body_size": len(response.get("content") or b""),
                "body": body_as_text(response),
                "duration_ms": round(1000 * (end - start), 1) if start and end else None,
            }
        messages = stream_messages(flow)
        if messages:
            decoder_name, decoder = stream_decoder_for(flow, opts)
            message_limit = opts.max_messages
            if message_limit is None:
                message_limit = 0 if decoder_name == "mqtt" else 20
            shown_messages = messages if message_limit == 0 else messages[:message_limit]
            entry["stream"] = {
                "protocol": decoder_name,
                "server": entry.get("server") or connection_summary(flow).replace("server connection: ", ""),
                "message_count": len(messages),
                "messages": [render_json_message(message, decoder, opts, stats["redactor"]) for message in shown_messages],
            }
        out.append(entry)
    return json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def render_json_message(message, decoder, opts, redactor):
    """One streamed message as a JSON object."""
    if not (isinstance(message, list) and len(message) == 3):
        return {"raw": as_text(message)}
    content = message[1] or b""
    item = {
        "timestamp": format_time(message[2]),
        "direction": "client -> server" if message[0] else "server -> client",
        "size": len(content),
    }
    if decoder is not None:
        item["decoded"] = decoder(content, opts, redactor)
    else:
        text = decode_text(decode_body(content))
        item["text" if text is not None else "preview"] = text if text is not None else preview_bytes(content[:48], opts)
    return item


def body_as_text(message):
    """Body of a message as text, None when it is binary."""
    return decode_text(decode_body(message.get("content") or b""))


def render_text(flows, opts, stats):
    """Readable transcript of the kept flows."""
    lines = [
        "# mitmproxy flow transcript",
        "# source: %s" % opts.source_label,
        "# flows: %d of %d kept" % (len(flows), stats["flows_total"]),
    ]
    if opts.keep_certs:
        lines.append("# certificates: kept")
    else:
        lines.append("# certificates: %d removed (%s)" % (stats["certs"], human_size(stats["certs_bytes"])))
    lines.append("# secrets: %s" % ("redacted as %s" % PLACEHOLDER if opts.redact else "kept as they are"))
    if stats["redactor"].reformatted:
        lines.append("# json bodies reformatted while redacting: %d" % stats["redactor"].reformatted)
    if opts.drop_content:
        lines.append("# bodies: dropped")
    elif opts.max_body:
        lines.append("# bodies: truncated to %d bytes" % opts.max_body)
    for index, flow in enumerate(flows, 1):
        lines.extend(render_text_flow(flow, index, opts, stats["redactor"]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_text_flow(flow, index, opts, redactor):
    """Transcript block of one flow."""
    request = flow.get("request")
    response = flow.get("response")
    lines = ["=" * 78]

    if isinstance(request, dict):
        lines.append(
            "[%d] %s  %s %s  (%s)"
            % (
                index,
                format_time(flow_timestamp(flow)),
                as_text(request.get("method")),
                flow_url(flow),
                as_text(request.get("http_version")),
            )
        )
        lines.append("-" * 78)
        lines.extend(render_text_headers(request, opts, ">"))
        block, note = render_text_body(request, opts)
        if block:
            lines.extend(block)
        if note:
            lines.append(note)
    else:
        lines.append("[%d] %s  %s flow, no HTTP request" % (index, format_time(flow_timestamp(flow)), as_text(flow.get("type"))))
        lines.append("-" * 78)
        lines.append(connection_summary(flow))
        lines.extend(render_text_messages(flow, opts, redactor))

    error = flow.get("error")
    if isinstance(error, dict) and error.get("msg"):
        lines.append("! flow error: %s" % as_text(error.get("msg")))

    if isinstance(response, dict):
        lines.append("-" * 78)
        lines.append(
            "RESPONSE %s %s  %s  (%s, %s)"
            % (
                response.get("status_code"),
                as_text(response.get("reason")),
                format_time(response.get("timestamp_start")),
                as_text(response.get("http_version")),
                flow_duration(flow),
            )
        )
        lines.extend(render_text_headers(response, opts, "<"))
        block, note = render_text_body(response, opts)
        if block:
            lines.extend(block)
        if note:
            lines.append(note)

    lines.append("")
    return lines


def flow_duration(flow):
    """Total duration of a flow, request start to response end."""
    request = flow.get("request") or {}
    response = flow.get("response") or {}
    start = request.get("timestamp_start")
    end = response.get("timestamp_end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return "duration n/a"
    return "%.1f ms total" % (1000 * (end - start))


def render_text_headers(message, opts, marker):
    """Header lines of one message, transport noise hidden by default."""
    lines = []
    for name, value in header_pairs(message):
        flat = normalize_name(name)
        if flat in opts.hide_headers:
            continue
        if flat in NOISE_HEADERS and not opts.show_noise_headers:
            continue
        lines.append(f"{marker} {as_text(name)}: {as_text(value)}")
    return ["headers:"] + lines if lines else []


def render_text_body(message, opts):
    """Return (body block, note) for one message body."""
    content = message.get("content") or b""
    if opts.drop_content:
        return [], "body: dropped (--drop-content)"
    if not content:
        return [], None
    label = "body: %d bytes, %s" % (len(content), header_value(message, "content-type") or "no content-type")
    decoded, encoding = decode_body_ex(content)
    text = decode_text(decoded)
    if encoding:
        label += " (decoded from %s)" % encoding
    if text is None:
        preview = bytes(decoded[:48]).hex(" ")
        return [label, "-----", "<binary, %d bytes, first bytes: %s>" % (len(content), preview), "-----"], None
    return ["", label, "-----", text.rstrip("\n"), "-----"], None


def render_text_messages(flow, opts, redactor):
    """Streamed messages of tcp/udp flows, decoded where the protocol is known."""
    messages = stream_messages(flow)
    if not messages:
        return []
    decoder_name, decoder = stream_decoder_for(flow, opts)
    message_limit = opts.max_messages
    if message_limit is None:
        message_limit = 0 if decoder_name == "mqtt" else 20
    shown_messages = messages if message_limit == 0 else messages[:message_limit]
    label = decoder_name if opts.decode == "auto" else "%s (forced)" % decoder_name
    lines = ["stream: %d messages, protocol %s" % (len(messages), label)]
    for message in shown_messages:
        if not (isinstance(message, list) and len(message) == 3):
            continue
        direction = "client -> server" if message[0] else "server -> client"
        content = message[1] or b""
        lines.append("  [%s] %s, %d bytes" % (format_time(message[2]), direction, len(content)))
        if decoder is not None:
            decoded = ["    " + line for line in decoder(content, opts, redactor)]
        else:
            decoded = render_stream_payload(content, opts, redactor, prefix="    ")
        lines.extend(decoded)
    if message_limit and len(messages) > message_limit:
        lines.append("  ... %d more messages omitted" % (len(messages) - message_limit))
    return lines


def render_stats(flows, opts, stats):
    """Inventory of the capture, to choose filters with."""
    hosts = Counter()
    methods = Counter()
    statuses = Counter()
    content_types = Counter()
    flow_types = Counter()
    body_bytes = 0
    streams = Counter()
    kept_ids = {id(flow) for flow in flows}

    for flow in stats["all_flows"]:
        flow_types[as_text(flow.get("type")) or "?"] += 1
        if id(flow) not in kept_ids:
            continue
        request = flow.get("request") or {}
        hosts[flow_host(flow) or "?"] += 1
        methods[as_text(request.get("method")) or "?"] += 1
        statuses[str(flow_status(flow) if flow_status(flow) is not None else "-")] += 1
        content_type = header_value(flow.get("response") or {}, "content-type") or header_value(request, "content-type") or "-"
        content_types[content_type.split(";")[0].strip()] += 1
        body_bytes += len(request.get("content") or b"")
        body_bytes += len((flow.get("response") or {}).get("content") or b"")
        if stream_messages(flow):
            streams[stream_decoder_for(flow, opts)[0]] += 1

    estimate = len(render_mitm(flows, opts, stats))
    lines = [
        "source: %s" % opts.source_label,
        "flows: %d total, %d kept, %d filtered out" % (stats["flows_total"], len(flows), stats["flows_total"] - len(flows)),
        "flow types: %s" % dict(flow_types),
        "",
        "hosts of kept flows:",
    ]
    lines.extend("  %4d  %s" % (count, host) for host, count in hosts.most_common())
    lines.extend(
        [
            "",
            "methods: %s" % dict(methods),
            "statuses: %s" % dict(statuses),
            "content types: %s" % dict(content_types.most_common(10)),
            "streamed flows by protocol: %s" % (dict(streams) or "none"),
            "body bytes kept: %s" % human_size(body_bytes),
            "",
            "noise:",
            "  TLS certificates in file: %d (%s)" % (stats["certs_total"], human_size(stats["certs_bytes_total"])),
            "  TLS certificates removed from kept flows: %d (%s)" % (stats["certs"], human_size(stats["certs_bytes"])),
            "  bodies truncated/dropped: %s in %d bodies" % (human_size(stats["body_bytes"]), stats["bodies_truncated"]),
            "  backup flow states removed: %d" % stats["backup"],
            "  secret values redacted: %d (%s)"
            % (
                sum(stats["redactor"].hits.values()),
                ", ".join("%s=%d" % (name, count) for name, count in stats["redactor"].hits.most_common(8)) or "none",
            ),
            "",
            "size: %s input, %s as a mitm flow file (%s smaller)"
            % (
                human_size(stats["bytes_in"]),
                human_size(estimate),
                "%.1f%%" % (100.0 * (1 - estimate / float(stats["bytes_in"]))) if stats["bytes_in"] else "0%",
            ),
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


RENDERERS = {
    "mitm": render_mitm,
    "json": render_json,
    "text": render_text,
    "stats": render_stats,
}


# *** Main flow ***


def new_stats():
    """Counters collected while cleaning, used by the renderers and report."""
    return {
        "flows_total": 0,
        "all_flows": [],
        "certs": 0,
        "certs_bytes": 0,
        "certs_total": 0,
        "certs_bytes_total": 0,
        "tls_fields": 0,
        "body_bytes": 0,
        "bodies_truncated": 0,
        "backup": 0,
        "bytes_in": 0,
        "bytes_out": 0,
        "streams": 0,
        "redactor": None,
    }


def count_certificates(flows):
    """Return (count, bytes) of all TLS certificates in the file."""
    count = 0
    size = 0
    for flow in flows:
        for side in ("client_conn", "server_conn"):
            certs = (flow.get(side) or {}).get("certificate_list") or []
            if certs:
                count += len(certs)
                size += len(tns_dumps(certs))
    return count, size


def read_input(path):
    """Read the whole flow file, or stdin when path is '-'."""
    try:
        if path == "-":
            return sys.stdin.buffer.read()
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as err:
        exit_with_error(f"cannot read '{path}': {err}")


def default_output_path(opts):
    """Return the output path for an input file that was not given one."""
    if opts.file == "-":
        name = "stdin"
    else:
        name = Path(opts.file).name
        for suffix in FLOW_SUFFIXES:
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]
                break
    if not name:
        name = "stdin"
    if name.endswith("-clean"):
        name = name[: -len("-clean")]
    if opts.format == "stats":
        filename = "%s-stats.txt" % name
    elif opts.format == "json":
        filename = "%s-clean.json" % name
    elif opts.format == "mitm":
        filename = "%s-clean.mitm" % name
    else:
        filename = "%s-clean" % name
    return Path(opts.output_dir) / filename


def write_output(opts, payload):
    """Write the payload to the output file, or stdout."""
    if opts.output == "-":
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
        return
    target = Path(opts.output)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    except OSError as err:
        exit_with_error(f"cannot write '{target}': {err}")


def report(opts, stats, kept):
    """Print the one line summary to stderr."""
    if opts.quiet or opts.format == "stats":
        return
    saved = 100.0 * (1 - stats["bytes_out"] / float(stats["bytes_in"])) if stats["bytes_in"] else 0.0
    target = "stdout" if opts.output == "-" else opts.output
    sys.stderr.write(
        "%s: %d/%d flows, %s -> %s (%.1f%% smaller), certificates removed: %d, "
        "secrets redacted: %d -> %s\n"
        % (
            TOOL,
            kept,
            stats["flows_total"],
            human_size(stats["bytes_in"]),
            human_size(stats["bytes_out"]),
            saved,
            stats["certs"],
            sum(stats["redactor"].hits.values()),
            target,
        )
    )
    if opts.format == "mitm" and stats["streams"] and opts.redact:
        sys.stderr.write(
            "%s: note: %d streamed flow(s) keep their raw bytes in mitm "
            "output, so secrets inside them are not redacted; use "
            "-f text or -f json to share them safely\n" % (TOOL, stats["streams"])
        )


def main():
    opts = parse_args()

    raw = read_input(opts.file)
    opts.source_label = opts.file

    stats = new_stats()
    stats["bytes_in"] = len(raw)
    try:
        flows = load_flows(raw)
    except ValueError as err:
        hint = ""
        if raw[:1] in (b"{", b"["):
            hint = " (looks like JSON/HAR: export a flow file with 'mitmdump -r <har> -w <flows>' first)"
        exit_with_error(f"'{opts.file}' is not a mitmproxy flow file: {err}{hint}")
    if not flows:
        exit_with_error("'%s' contains no flows" % opts.file)
    stats["flows_total"] = len(flows)
    stats["all_flows"] = flows
    stats["certs_total"], stats["certs_bytes_total"] = count_certificates(flows)

    stats["redactor"] = Redactor(
        opts.redact, opts.redact_header, opts.redact_param, opts.keep_header, opts.keep_param, opts.redact_value
    )
    cleaner = Cleaner(opts, stats["redactor"], stats)
    flow_filter = FlowFilter(opts)

    kept = []
    for flow in flows:
        if not flow_filter.matches(flow):
            continue
        cleaner.clean(flow)
        kept.append(flow)
    if not kept and opts.format != "stats":
        exit_with_error("no flow left after filtering")

    payload = RENDERERS[opts.format](kept, opts, stats)
    stats["bytes_out"] = len(payload)
    write_output(opts, payload)
    report(opts, stats, len(kept))
    return 0


# *** Usage and argument parsing ***


def build_parser():
    parser = argparse.ArgumentParser(
        prog=TOOL,
        description="Trim a mitmproxy flow file to the relevant proxied communication.",
        epilog="""examples:
  %(prog)s capture.mitm --host '*.example.com'
  %(prog)s capture.mitm -f stats
  %(prog)s capture.mitm --only-errors --max-body 4096 --no-redact
  %(prog)s capture.mitm -f mitm --drop-content -o clean.mitm
""",
    )
    parser.add_argument("file", metavar="FLOW_FILE", help="mitmproxy flow file, or - for stdin")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write to FILE instead of data/flows/<name>-clean; '-' writes to stdout",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=str(DEFAULT_OUTPUT_DIR),
        help="directory for the default output path (default: data/flows)",
    )
    parser.add_argument("-f", "--format", choices=sorted(RENDERERS), default="text", help="output format (default: text)")
    parser.add_argument("-q", "--quiet", action="store_true", help="do not print the summary line to stderr")

    group = parser.add_argument_group("flow selection")
    group.add_argument("--host", action="append", default=[], metavar="GLOB", help="keep only this host, glob, repeatable")
    group.add_argument("--exclude-host", action="append", default=[], metavar="GLOB", help="drop this host, glob, repeatable")
    group.add_argument("--path", action="append", default=[], metavar="TEXT", help="keep only paths containing TEXT, repeatable")
    group.add_argument("--path-regex", metavar="REGEX", help="keep only paths matching REGEX")
    group.add_argument(
        "--method", action="append", default=[], metavar="LIST", help="keep only these methods, e.g. POST or GET,POST"
    )
    group.add_argument(
        "--status", action="append", default=[], metavar="LIST", help="keep only these statuses, e.g. 404 or 4xx,500"
    )
    group.add_argument(
        "--content-type", action="append", default=[], metavar="GLOB", help="keep only this content type, glob, repeatable"
    )
    group.add_argument(
        "--flow-type", action="append", default=[], metavar="LIST", help="keep only these flow types, e.g. http,tcp"
    )
    group.add_argument(
        "--only-errors", action="store_true", help="keep only failed flows (flow error, no response or status >= 400)"
    )
    group.add_argument("--skip-errors", action="store_true", help="drop failed flows")

    group = parser.add_argument_group("content")
    group.add_argument(
        "--drop-content", action="store_true", help="remove all request and response bodies (wins over --max-body)"
    )
    group.add_argument(
        "--max-body", type=int, default=0, metavar="BYTES", help="truncate bodies to BYTES, 0 keeps them (default: 0)"
    )
    group.add_argument(
        "--max-messages",
        type=int,
        default=None,
        metavar="N",
        help="cap messages shown per stream (default: 20 for raw streams; all MQTT messages)",
    )
    group.add_argument(
        "--max-stream-payload",
        type=int,
        default=None,
        metavar="BYTES",
        help="cap payload bytes per stream message (default: 2048 for raw streams; unlimited for MQTT text)",
    )
    group.add_argument(
        "--max-topics", type=int, default=20, metavar="N", help="MQTT topic filters listed per packet (default: 20)"
    )
    group.add_argument(
        "--decode",
        choices=("auto", "off", "mqtt"),
        default="auto",
        help="decode streamed protocols: auto, off or mqtt (default: auto)",
    )
    group.add_argument(
        "--preview", choices=("hex", "base64"), default="hex", help="how to show undecodable binary bytes (default: hex)"
    )
    group.add_argument(
        "--full-binary",
        action="store_true",
        help="include complete opaque binary payloads; requires --no-redact",
    )

    group = parser.add_argument_group("redaction")
    group.add_argument("--no-redact", dest="redact", action="store_false", default=True, help="keep secrets as they are")
    group.add_argument(
        "--redact-header", action="append", default=[], metavar="NAME", help="also redact this header name, repeatable"
    )
    group.add_argument(
        "--redact-param", action="append", default=[], metavar="NAME", help="also redact this query/body/json name, repeatable"
    )
    group.add_argument(
        "--redact-value", action="append", default=[], metavar="REGEX", help="also redact values matching REGEX, repeatable"
    )
    group.add_argument(
        "--keep-header", action="append", default=[], metavar="NAME", help="never redact this header name, repeatable"
    )
    group.add_argument(
        "--keep-param", action="append", default=[], metavar="NAME", help="never redact this query/body/json name, repeatable"
    )

    group = parser.add_argument_group("noise removal")
    group.add_argument("--keep-certs", action="store_true", help="keep the TLS certificate chains")
    group.add_argument("--keep-tls", action="store_true", help="keep cipher lists and ALPN offers")
    group.add_argument("--show-noise-headers", action="store_true", help="show transport headers hidden by default")
    group.add_argument(
        "--hide-header", action="append", default=[], metavar="NAME", help="hide this header in text output, repeatable"
    )
    parser.add_argument("--version", action="version", version=f"{TOOL} {VERSION}")
    return parser


def parse_args(argv=None):
    """Parse and validate the command line."""
    parser = build_parser()
    opts = parser.parse_args(argv)
    if opts.max_body < 0:
        parser.error("--max-body must not be negative")
    if opts.max_messages is not None and opts.max_messages < 0:
        parser.error("--max-messages must not be negative")
    if opts.max_stream_payload is not None and opts.max_stream_payload < 0:
        parser.error("--max-stream-payload must not be negative")
    if opts.max_topics < 0:
        parser.error("--max-topics must not be negative")
    if opts.output is None:
        opts.output = str(default_output_path(opts))
    if opts.output != "-" and opts.file != "-" and Path(opts.output).resolve() == Path(opts.file).resolve():
        parser.error("the output would overwrite the input; choose another -o or --output-dir")
    if opts.full_binary and opts.redact:
        parser.error("--full-binary requires --no-redact because opaque bytes cannot be safely redacted")
    opts.hide_headers = {normalize_name(name) for name in opts.hide_header}
    return opts


# *** Entrypoint ***


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
    except KeyboardInterrupt:
        raise SystemExit(130)
