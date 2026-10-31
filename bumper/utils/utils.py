"""Utils module."""

import asyncio
from collections.abc import Awaitable, Coroutine
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, overload

from aiohttp import AsyncResolver
import validators

from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)


def store_service(coro: Coroutine[Any, Any, None]) -> None:
    """Create and store a new asyncio task."""
    task = asyncio.create_task(coro)
    bumper_isc.background_tasks.add(task)
    task.add_done_callback(bumper_isc.background_tasks.discard)


async def with_timeout(coro: Awaitable[Any], seconds: int = 3) -> Any:
    """Wait with timeout helper."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except TimeoutError:
        return "timeout"


async def check_file_exists(file: Path) -> bool:
    """Check if a file exists."""
    try:
        # Use asyncio.to_thread for blocking Path.exists()
        return await asyncio.to_thread(file.exists)
    except Exception:
        return False


def default_log_warn_not_impl(func: str) -> None:
    """Get default log warn for not implemented."""
    _LOGGER.debug(f"!!! POSSIBLE THIS API IS NOT (FULL) IMPLEMENTED :: {func} !!!")


def default_exception_str_builder(e: Exception | None = None, info: str | None = None) -> str:
    """Build default exception message."""
    i_error = ""
    i_info = ""
    if e is not None:
        i_error = f" :: {e}"
    if info is not None:
        i_info = f" :: {info}"
    return f"Unexpected exception occurred{i_info}{i_error}"


def convert_to_millis(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return round(seconds * 1000)


# A timestamp below this limit is a number of seconds, not of milliseconds.
_SECONDS_LIMIT = 100_000_000_000


def to_milliseconds(timestamp: int) -> int:
    """Return a timestamp in milliseconds.

    The robot sends the time of a picture in milliseconds and the time of a map
    in seconds. A number of seconds is scaled up; a number of milliseconds is
    left alone.

    A number of seconds of today is between one billion (2001) and a hundred
    billion (the year 5138), while a number of milliseconds of today is above a
    hundred billion. The values that are too small to be a time of today are
    left alone as well.
    """
    if 1_000_000_000 <= timestamp < _SECONDS_LIMIT:
        return timestamp * 1000
    return timestamp


def get_current_time_as_millis() -> int:
    """Get current time in millis."""
    return convert_to_millis(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())


def get_millis_to_iso_z(ms: int) -> str:
    """Convert millis timestamp to ISO 8601 UTC string ending with 'Z'."""
    dt = datetime.fromtimestamp(ms / 1000, tz=bumper_isc.LOCAL_TIMEZONE)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get_tzm_and_ts() -> tuple[int, int]:
    """Get tzm offset and current timestamp (seconds)."""
    now = datetime.now(bumper_isc.LOCAL_TIMEZONE)
    # UTC offset in minutes (DST-aware)
    if not (offset := now.utcoffset()):
        msg = "UTC offset is not set!"
        raise ValueError(msg)
    offset_minutes = int(offset.total_seconds() // 60)
    # Current timestamp in milliseconds
    timestamp_s = int(time.time())
    return offset_minutes, timestamp_s


@overload
def to_int(value: Any) -> int | None: ...


@overload
def to_int(value: Any, default: int) -> int: ...


def to_int(value: Any, default: int | None = None) -> int | None:
    """Convert a value to int, falling back to `default` when it cannot be."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_resolver_with_public_nameserver() -> AsyncResolver:
    """Get resolver."""
    # requires aiodns
    return AsyncResolver(nameservers=bumper_isc.PROXY_NAMESERVERS)


async def resolve(host: str) -> str:
    """Resolve host."""
    hosts = await get_resolver_with_public_nameserver().resolve(host)
    return str(hosts[0]["host"])


def is_valid_url(url: str | None) -> bool:
    """Validate if is a url."""
    return bool(validators.url(url))


def is_valid_ip(ip: str | None) -> bool:
    """Validate if is ipv4 or ipv6."""
    return bool(validators.ipv4(ip) or validators.ipv6(ip))


def get_dc_code(area_code: str) -> str:
    """Return to a area code the corresponding dc code."""
    return get_area_code_map().get(area_code, "na")


def get_area_code_map() -> dict[str, str]:
    """Return area code map."""
    config_path = Path(__file__).parent / "utils_area_code_mapping.json"
    try:
        patterns = json.loads(config_path.read_text())
        if isinstance(patterns, dict):
            return patterns
    except Exception:
        _LOGGER.warning(f"Could not find or read: '{config_path.name}'")
    return {}


def load_json_array_files(filenames: list[str | Path], base_path: Path) -> list[dict[str, Any]]:
    """Load and combine JSON arrays from one or more files located under provided base_path."""
    combined: list[dict[str, Any]] = []

    for fn in filenames:
        file_path = base_path / fn
        data = []
        try:
            data = json.loads(file_path.read_text())
        except FileNotFoundError:
            _LOGGER.exception(f"JSON file not found: {file_path}")
            raise
        except json.JSONDecodeError:
            _LOGGER.exception(f"Invalid JSON in file {file_path}")
            raise

        if not isinstance(data, list):
            msg = f"JSON file {file_path.name} must contain a top-level array."
            _LOGGER.error(msg)
            raise TypeError(msg)

        combined.extend(data)

    return combined


def load_json_object_files(filename: str | Path, base_path: Path) -> dict[str, Any]:
    """Load JSON object from a file."""
    data: Any = {}
    file_path = base_path / filename
    try:
        data = json.loads(file_path.read_text())
    except FileNotFoundError:
        _LOGGER.exception(f"JSON file not found: {file_path}")
        raise
    except json.JSONDecodeError:
        _LOGGER.exception(f"Invalid JSON in file {file_path}")
        raise

    if not isinstance(data, dict):
        msg = f"JSON file {file_path.name} must contain a top-level object."
        _LOGGER.error(msg)
        raise TypeError(msg)

    return data


def load_text_files(filename: str | Path, base_path: Path) -> str:
    """Load TEXT from a file."""
    data: str = ""
    file_path = base_path / filename
    try:
        data = file_path.read_text()
    except FileNotFoundError:
        _LOGGER.exception(f"JSON file not found: {file_path}")
        raise

    return data
