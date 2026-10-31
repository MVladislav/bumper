"""Parse error reports sent by Ecovacs robots."""

from dataclasses import dataclass
import json
import re

import defusedxml.ElementTree as ET  # noqa: N817
from defusedxml.common import DefusedXmlException


@dataclass(frozen=True)
class DeviceErrorReport:
    """One robot-reported error-state update."""

    codes: tuple[int, ...]
    previous_codes: tuple[int, ...]
    reported_at: int | None
    kind: str
    payload: str


def parse_device_error_report(payload: str) -> DeviceErrorReport | None:
    """Parse the error-event XML formats observed from robots.

    MQTT broadcasts use ``td="errors"`` with ``old`` and ``new`` attributes.
    XML P2P GetError responses carry ``errs`` and may not have a ``td`` value.
    An empty code value is a valid clear event, represented by an empty tuple.
    """
    if len(payload) > 4096:
        return None

    if payload.lstrip().startswith("{"):
        return _parse_json_get_error(payload)

    try:
        root = ET.fromstring(payload)
    except (DefusedXmlException, ET.ParseError):
        return None

    ctl = root if _local_name(root.tag) == "ctl" else next((item for item in root.iter() if _local_name(item.tag) == "ctl"), None)
    if ctl is None:
        return None

    kind = ctl.get("td")
    if kind == "errors":
        if "new" not in ctl.attrib:
            return None
        codes = _parse_codes(ctl.get("new", ""))
        previous_codes = _parse_codes(ctl.get("old", ""))
    elif kind == "error" or "errs" in ctl.attrib:
        if "errs" not in ctl.attrib:
            return None
        codes = _parse_codes(ctl.get("errs", ""))
        previous_codes = ()
        kind = kind or "getError"
    else:
        return None

    reported_at = _parse_timestamp(ctl.get("ts"))
    report_payload = ET.tostring(ctl, encoding="unicode")
    return DeviceErrorReport(codes, previous_codes, reported_at, kind, report_payload)


def _parse_json_get_error(payload: str) -> DeviceErrorReport | None:
    """Parse the P2P GetError response shape used by newer robot classes."""
    try:
        response = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(response, dict):
        return None

    response_body = response.get("resp", response)
    if not isinstance(response_body, dict):
        return None
    body = response_body.get("body")
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict):
        get_error = data.get("getError")
        if isinstance(get_error, dict):
            data = get_error.get("data")
    codes = data.get("code") if isinstance(data, dict) else None
    if not isinstance(codes, list):
        return None

    last_code = codes[-1] if codes else 0
    if not isinstance(last_code, int) or isinstance(last_code, bool):
        return None
    active_codes = () if last_code == 0 else (last_code,)

    header = response_body.get("header")
    timestamp = header.get("ts") if isinstance(header, dict) else None
    reported_at = _parse_timestamp(str(timestamp)) if timestamp is not None else None
    return DeviceErrorReport(active_codes, (), reported_at, "getError", payload)


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace prefix."""
    return tag.rsplit("}", maxsplit=1)[-1].rsplit(":", maxsplit=1)[-1]


def _parse_codes(value: str) -> tuple[int, ...]:
    """Parse a comma- or whitespace-separated set of numeric error codes."""
    codes: list[int] = []
    for part in re.split(r"[,;\s]+", value.strip()):
        if not part:
            continue
        try:
            code = int(part)
        except ValueError:
            continue
        if code not in codes:
            codes.append(code)
    return tuple(codes)


def _parse_timestamp(value: str | None) -> int | None:
    """Parse a robot timestamp without interpreting its time unit."""
    if value is None:
        return None
    try:
        timestamp = int(value)
    except ValueError:
        return None
    return timestamp if timestamp >= 0 else None
