"""Tests for recording robot error reports in runtime memory."""

import logging

import pytest

from bumper.utils.device_error_handler import discard_device_error_report, get_device_error_report, record_device_error_report


def test_record_device_error_report_stores_only_live_state() -> None:
    """Keep the report in memory without creating or changing a database bot."""
    did = "runtime-did-1"
    discard_device_error_report(did)
    try:
        changed = record_device_error_report(did, "mqtt", '<ctl ts="1234" td="errors" old="" new="520"/>')

        report = get_device_error_report(did)
        assert changed is True
        assert report is not None
        assert report.codes == (520,)
        assert report.reported_at == 1234
        assert report.source == "mqtt"
        assert 'new="520"' in report.payload
    finally:
        discard_device_error_report(did)


def test_record_device_error_report_warns_only_when_error_state_changes(caplog: pytest.LogCaptureFixture) -> None:
    """Warn when a new active error arrives, without noisy repeats."""
    did = "runtime-did-2"
    discard_device_error_report(did)
    payload = '<ctl td="errors" old="" new="520"/>'
    try:
        with caplog.at_level(logging.WARNING):
            assert record_device_error_report(did, "mqtt", payload) is True
            assert record_device_error_report(did, "mqtt", payload) is False

        assert "Robot reported device error(s)" in caplog.text
        assert caplog.text.count("Robot reported device error(s)") == 1
    finally:
        discard_device_error_report(did)


def test_record_device_error_report_clears_active_codes() -> None:
    """An empty MQTT transition records that the live error was cleared."""
    did = "runtime-did-3"
    discard_device_error_report(did)
    try:
        record_device_error_report(did, "mqtt", '<ctl td="errors" old="" new="520"/>')
        changed = record_device_error_report(did, "mqtt", '<ctl td="errors" old="520" new=""/>')

        report = get_device_error_report(did)
        assert changed is True
        assert report is not None
        assert report.codes == ()
        assert report.previous_codes == (520,)
    finally:
        discard_device_error_report(did)


def test_json_clear_keeps_the_previous_active_code() -> None:
    """Keep the cleared code available when JSON GetError reports only zero."""
    did = "runtime-did-json-clear"
    discard_device_error_report(did)
    try:
        record_device_error_report(did, "mqtt-p2p", '{"body":{"data":{"code":[520]}}}')
        changed = record_device_error_report(did, "mqtt-p2p", '{"body":{"data":{"code":[0]}}}')

        report = get_device_error_report(did)
        assert changed is True
        assert report is not None
        assert report.codes == ()
        assert report.previous_codes == (520,)
    finally:
        discard_device_error_report(did)
