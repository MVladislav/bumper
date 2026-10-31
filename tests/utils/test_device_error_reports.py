"""Tests for parsing robot-reported device error events."""

from bumper.utils.device_error_reports import parse_device_error_report


def test_parse_mqtt_error_transition() -> None:
    """Parse the MQTT atr/errors transition format."""
    report = parse_device_error_report('<ctl ts="1560904925396" td="errors" old="102" new="110,520"/>')

    assert report is not None
    assert report.kind == "errors"
    assert report.codes == (110, 520)
    assert report.previous_codes == (102,)
    assert report.reported_at == 1560904925396


def test_parse_mqtt_error_clear() -> None:
    """An empty new value represents an error-clear event."""
    report = parse_device_error_report('<ctl td="errors" old="110" new=""/>')

    assert report is not None
    assert report.codes == ()
    assert report.previous_codes == (110,)


def test_parse_legacy_control_error() -> None:
    """Parse a legacy ctl error report with one or more codes."""
    report = parse_device_error_report('<iq><query><ctl td="error" errs="102 520"/></query></iq>')

    assert report is not None
    assert report.kind == "error"
    assert report.codes == (102, 520)
    assert report.previous_codes == ()


def test_parse_xml_get_error_response_without_td() -> None:
    """The XML P2P GetError response carries errs without a td attribute."""
    report = parse_device_error_report('<ctl ret="ok" errs="105"/>')

    assert report is not None
    assert report.kind == "getError"
    assert report.codes == (105,)


def test_parse_json_get_error_response_uses_last_code() -> None:
    """Newer robot classes report GetError codes in a P2P JSON body."""
    payload = (
        '{"header":{"ts":"1793456317228356743"},"body":{"code":0,"msg":"ok","data":'
        '{"getError":{"code":0,"msg":"ok","data":{"code":[105,520]}}}}}'
    )

    report = parse_device_error_report(payload)

    assert report is not None
    assert report.kind == "getError"
    assert report.codes == (520,)
    assert report.reported_at == 1793456317228356743


def test_parse_json_get_error_clear() -> None:
    """An empty list or a final zero code indicates no active error."""
    for codes in ([], [105, 0]):
        report = parse_device_error_report(f'{{"body":{{"data":{{"code":{codes!r}}}}}}}')
        assert report is not None
        assert report.codes == ()


def test_ignore_non_error_and_malformed_payloads() -> None:
    """Do not mistake unrelated or malformed robot messages for errors."""
    assert parse_device_error_report('<ctl td="battery" power="80"/>') is None
    assert parse_device_error_report("<ctl td='errors' new='110'>") is None
    assert parse_device_error_report("x" * 4097) is None
