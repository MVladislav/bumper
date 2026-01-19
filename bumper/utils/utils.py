"""Utils module."""

import asyncio
from collections.abc import Awaitable, Coroutine
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import time
from typing import Any

from aiohttp import AsyncResolver
import validators

from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)

# ******************************************************************************


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


# ******************************************************************************


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


# ******************************************************************************


def convert_to_millis(seconds: float) -> int:
    """Convert seconds to milliseconds."""
    return round(seconds * 1000)


def get_current_time_as_millis() -> int:
    """Get current time in millis."""
    return convert_to_millis(datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())


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


def str_to_bool(value: str | int | bool | None) -> bool:
    """Convert str to bool."""
    return str(value).lower() in ["true", "1", "t", "y", "on", "yes"]


def to_int(value: Any) -> int | None:
    """Convert save any to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ******************************************************************************


def get_resolver_with_public_nameserver() -> AsyncResolver:
    """Get resolver."""
    # requires aiodns
    return AsyncResolver(nameservers=bumper_isc.PROXY_NAMESERVER)


async def resolve(host: str) -> str:
    """Resolve host."""
    hosts = await get_resolver_with_public_nameserver().resolve(host)
    return str(hosts[0]["host"])


# ******************************************************************************


def is_valid_url(url: str | None) -> bool:
    """Validate if is a url."""
    return bool(validators.url(url))


def is_valid_ip(ip: str | None) -> bool:
    """Validate if is ipv4 or ipv6."""
    return bool(validators.ipv4(ip) or validators.ipv6(ip))


# ******************************************************************************


def get_dc_code(area_code: str) -> str:
    """Return to a area code the corresponding dc code."""
    return get_area_code_map().get(area_code, "na")


def get_area_code_map() -> dict[str, str]:
    """Return area code map."""
    config_path = Path(__file__).parent / "utils_area_code_mapping.json"
    try:
        with config_path.open(encoding="utf-8") as file:
            patterns = json.load(file)
            if isinstance(patterns, dict):
                return patterns
    except Exception:
        _LOGGER.warning(f"Could not find or read: '{config_path.name}'")
    return {}


def check_url_not_used(url: str) -> bool:
    """Check if a url is not in the know api list, used in the middleware for debug."""
    config_path = Path(__file__).parent / "utils_implemented_apis.json"
    try:
        with config_path.open(encoding="utf-8") as file:
            patterns = json.load(file)
            if isinstance(patterns, list):
                return any(re.search(pattern, url) for pattern in patterns)
    except Exception:
        _LOGGER.warning(f"Could not find or read: '{config_path.name}'")
    return False
