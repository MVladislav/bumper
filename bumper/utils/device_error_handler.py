"""Keep the latest live robot error reports in process memory."""

from dataclasses import dataclass
from datetime import datetime
import logging

from bumper.db import bot_repo
from bumper.utils.device_error_reports import parse_device_error_report
from bumper.utils.device_errors import DEVICE_ERRORS_BY_CODE, describe

_LOGGER = logging.getLogger(__name__)
_MAX_LIVE_ERROR_REPORTS = 256


@dataclass(frozen=True)
class LiveDeviceErrorReport:
    """Most recent device-error report held for the current process only."""

    codes: tuple[int, ...]
    previous_codes: tuple[int, ...]
    reported_at: int | None
    received_at: str
    source: str
    payload: str


_LIVE_DEVICE_ERROR_REPORTS: dict[str, LiveDeviceErrorReport] = {}


def record_device_error_report(did: str, source: str, payload: str) -> bool:
    """Keep the latest parsed error report and return whether active codes changed."""
    if report := parse_device_error_report(payload):
        bot = bot_repo.get_by_did_or_name(did)
        report_did = bot.did if bot is not None else did
        previous = _LIVE_DEVICE_ERROR_REPORTS.get(report_did)
        previous_codes = report.previous_codes
        if not report.codes and not previous_codes and previous is not None:
            previous_codes = previous.codes or previous.previous_codes
        _LIVE_DEVICE_ERROR_REPORTS[report_did] = LiveDeviceErrorReport(
            report.codes,
            previous_codes,
            report.reported_at,
            datetime.now().astimezone().isoformat(timespec="seconds"),
            source,
            report.payload,
        )
        if len(_LIVE_DEVICE_ERROR_REPORTS) > _MAX_LIVE_ERROR_REPORTS:
            oldest = min(_LIVE_DEVICE_ERROR_REPORTS, key=lambda key: _LIVE_DEVICE_ERROR_REPORTS[key].received_at)
            del _LIVE_DEVICE_ERROR_REPORTS[oldest]

        changed = previous is None or previous.codes != report.codes
        if changed and report.codes:
            descriptions = [
                f"{DEVICE_ERRORS_BY_CODE[code].name}: {describe(code)}" if code in DEVICE_ERRORS_BY_CODE else describe(code)
                for code in report.codes
            ]
            _LOGGER.warning(
                f"Robot reported device error(s) :: codes={report.codes} :: details={descriptions} :: source={source}",
            )
        elif changed:
            _LOGGER.info(f"Robot cleared its reported device error(s) :: source={source}")
        return changed
    return False


def get_device_error_report(did: str) -> LiveDeviceErrorReport | None:
    """Return this process's latest error report for a bot, if present."""
    return _LIVE_DEVICE_ERROR_REPORTS.get(did)


def discard_device_error_report(did: str) -> None:
    """Forget a bot's runtime error report when its record is removed."""
    _LIVE_DEVICE_ERROR_REPORTS.pop(did, None)
