import datetime as dt
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from aiohttp import AsyncResolver
import pytest

from bumper.utils import utils
from bumper.utils.settings import config as bumper_isc

# Assuming _LOGGER is a logger instance, you can use a test logger for capturing logs in tests
test_logger = logging.getLogger("test_logger")


def test_default_log_warn_not_impl(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    func_name = "some_function"
    utils.default_log_warn_not_impl(func_name)

    assert f"POSSIBLE THIS API IS NOT (FULL) IMPLEMENTED :: {func_name}" in caplog.text


def test_default_exception_str_builder() -> None:
    exception_msg = "An error occurred"
    info_msg = "Some additional info"
    e = Exception(exception_msg)

    result = utils.default_exception_str_builder(info=info_msg)
    assert f"Unexpected exception occurred :: {info_msg}" == result

    result = utils.default_exception_str_builder(e=e, info=info_msg)
    assert f"Unexpected exception occurred :: {info_msg} :: {e}" == result


def test_default_exception_str_builder_no_info() -> None:
    exception_msg = "An error occurred"
    e = Exception(exception_msg)

    result = utils.default_exception_str_builder(e=e)
    assert f"Unexpected exception occurred :: {e}" == result

    result = utils.default_exception_str_builder()
    assert result == "Unexpected exception occurred"


# ******************************************************************************


def test_get_milli_time() -> None:
    assert (
        utils.convert_to_millis(dt.datetime(2018, 1, 1, 1, 0, 0, 0, tzinfo=bumper_isc.LOCAL_TIMEZONE).timestamp())
        == 1514768400000
    )


def test_get_current_time_as_millis() -> None:
    # Get the current time in milliseconds using the function
    current_time = utils.get_current_time_as_millis()

    # Get the current time using Python's datetime module
    expected_time = int(dt.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp() * 1000)

    # Assert that the current time obtained from the function is close to the expected time
    # This is to account for potential slight variations due to the time it takes to execute the test
    assert abs(current_time - expected_time) < 1000, "Current time in milliseconds is not within an acceptable range."


def test_get_tzm_and_ts() -> None:
    bumper_isc.LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")
    offset_minutes, timestamp_s = utils.get_tzm_and_ts()
    assert timestamp_s == int(dt.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).timestamp())
    assert offset_minutes == int(dt.datetime.now(tz=bumper_isc.LOCAL_TIMEZONE).utcoffset().total_seconds() // 60)


def test_get_tzm_and_ts_raises() -> None:
    bumper_isc.LOCAL_TIMEZONE = ZoneInfo("UTC")
    with pytest.raises(ValueError, match="UTC offset is not set!"):
        _, _ = utils.get_tzm_and_ts()


def test_to_milliseconds_scales_seconds() -> None:
    """A number of seconds is scaled up."""
    # The robot sends the time of a map in seconds.
    assert utils.to_milliseconds(1792439780) == 1792439780000


def test_to_milliseconds_keeps_milliseconds() -> None:
    """A number of milliseconds is left alone."""
    # The robot sends the time of a picture in milliseconds.
    assert utils.to_milliseconds(1746022105000) == 1746022105000


def test_to_milliseconds_keeps_small_values() -> None:
    """A value that is too small to be a time of today is left alone."""
    assert utils.to_milliseconds(1000) == 1000
    assert utils.to_milliseconds(0) == 0


def test_to_milliseconds_at_the_edges() -> None:
    """The edges of the range of seconds are handled."""
    assert utils.to_milliseconds(999_999_999) == 999_999_999
    assert utils.to_milliseconds(1_000_000_000) == 1_000_000_000_000
    assert utils.to_milliseconds(99_999_999_999) == 99_999_999_999_000
    assert utils.to_milliseconds(100_000_000_000) == 100_000_000_000


def test_to_int() -> None:
    """A value converts to int or falls back to the default."""
    assert utils.to_int("5") == 5
    assert utils.to_int(3.7) == 3
    assert utils.to_int(None) is None
    assert utils.to_int("nope", 0) == 0
    assert utils.to_int(None, 7) == 7
    assert utils.to_int({"a": 1}, -1) == -1


async def test_get_resolver_with_public_nameserver() -> None:
    """A resolver is built from the configured public nameservers."""
    resolver = utils.get_resolver_with_public_nameserver()
    assert isinstance(resolver, AsyncResolver)


def test_load_json_array_files_combines_arrays(tmp_path: Path) -> None:
    """Arrays of several files are combined in order."""
    (tmp_path / "a.json").write_text(json.dumps([{"x": 1}, {"x": 2}]))
    (tmp_path / "b.json").write_text(json.dumps([{"y": 3}]))
    assert utils.load_json_array_files(["a.json", "b.json"], tmp_path) == [{"x": 1}, {"x": 2}, {"y": 3}]


def test_load_json_array_files_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        utils.load_json_array_files(["missing.json"], tmp_path)


def test_load_json_array_files_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("not json")
    with pytest.raises(json.JSONDecodeError):
        utils.load_json_array_files(["bad.json"], tmp_path)


def test_load_json_array_files_non_array_raises(tmp_path: Path) -> None:
    (tmp_path / "obj.json").write_text(json.dumps({"a": 1}))
    with pytest.raises(TypeError, match="top-level array"):
        utils.load_json_array_files(["obj.json"], tmp_path)


def test_load_json_object_files_reads_object(tmp_path: Path) -> None:
    (tmp_path / "o.json").write_text(json.dumps({"a": 1}))
    assert utils.load_json_object_files("o.json", tmp_path) == {"a": 1}


def test_load_json_object_files_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        utils.load_json_object_files("missing.json", tmp_path)


def test_load_json_object_files_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("not json")
    with pytest.raises(json.JSONDecodeError):
        utils.load_json_object_files("bad.json", tmp_path)


def test_load_json_object_files_non_object_raises(tmp_path: Path) -> None:
    (tmp_path / "arr.json").write_text(json.dumps([1, 2]))
    with pytest.raises(TypeError, match="top-level object"):
        utils.load_json_object_files("arr.json", tmp_path)


def test_load_text_files_reads_text(tmp_path: Path) -> None:
    (tmp_path / "t.txt").write_text("hello")
    assert utils.load_text_files("t.txt", tmp_path) == "hello"


def test_load_text_files_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        utils.load_text_files("missing.txt", tmp_path)


# ******************************************************************************
