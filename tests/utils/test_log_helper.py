import logging

import pytest

from bumper.utils.log_helper import AioHttpFilter, AmqttFilter, LogHelper, SanitizeFilter


@pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
def test_log_helper_init(level: str, log_helper: LogHelper, caplog: pytest.LogCaptureFixture) -> None:
    assert isinstance(log_helper, LogHelper)

    # Check that log level is set correctly
    assert logging.getLogger("root").getEffectiveLevel() == level

    # Ensure that SanitizeFilter is added to the root handler
    sanitize_filter_added = False
    for handler in logging.getLogger("root").handlers:
        if len(handler.filters) > 0 and isinstance(handler.filters[0], SanitizeFilter):
            sanitize_filter_added = True
            break
    assert sanitize_filter_added

    # Check that AioHttpFilter is added to the aiohttp.access logger
    aiohttp_access_logger = logging.getLogger("aiohttp.access")
    assert isinstance(aiohttp_access_logger.filters[0], AioHttpFilter)

    # Check that AmqttFilter is added to the amqtt.broker logger
    amqtt_broker_logger = logging.getLogger("amqtt.broker")
    assert isinstance(amqtt_broker_logger.filters[0], AmqttFilter)

    # Test log message
    logging.getLogger().log(level, "Test log message")
    assert "Test log message" in caplog.text


def test_log_helper_clean_logs() -> None:
    logger_name_size = LogHelper()._clean_logs()
    assert logger_name_size > 0


@pytest.mark.usefixtures("log_helper")
@pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
def test_aiohttp_filter(level: int) -> None:
    aiohttp_filter = AioHttpFilter()

    # Test suppress 'aiohttp.access'
    record = logging.LogRecord(
        name="aiohttp.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args=None,
        exc_info=None,
    )
    if level == logging.DEBUG:
        assert aiohttp_filter.filter(record)
    if level == logging.INFO:
        assert not aiohttp_filter.filter(record)
    assert record.levelno == logging.INFO

    # Test other loggers not affected
    record = logging.LogRecord(
        name="some_other_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args=None,
        exc_info=None,
    )
    assert aiohttp_filter.filter(record)
    assert record.levelno == logging.INFO


@pytest.mark.usefixtures("log_helper")
@pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
def test_amqtt_filter(level: int) -> None:
    amqtt_filter = AmqttFilter()

    # Test suppress 'amqtt.broker' for "No more data"
    record = logging.LogRecord(
        name="amqtt.broker",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="No more data",
        args=None,
        exc_info=None,
    )
    if level == logging.DEBUG:
        assert amqtt_filter.filter(record)
    if level == logging.INFO:
        assert not amqtt_filter.filter(record)
    assert record.levelno == logging.WARNING

    # Test suppress 'amqtt.broker' for "No more data"
    record = logging.LogRecord(
        name="amqtt.broker",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="No more data",
        args=None,
        exc_info=None,
    )
    if level == logging.DEBUG:
        assert amqtt_filter.filter(record)
    if level == logging.INFO:
        assert not amqtt_filter.filter(record)
    assert record.levelno == logging.ERROR

    # Test not suppress 'amqtt' for others
    record = logging.LogRecord(
        name="amqtt",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="No more data",
        args=None,
        exc_info=None,
    )
    assert amqtt_filter.filter(record)
    assert record.levelno == logging.WARNING

    # Test not suppress 'amqtt.broker' for others
    record = logging.LogRecord(
        name="amqtt.broker",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="No more test data",
        args=None,
        exc_info=None,
    )
    assert amqtt_filter.filter(record)
    assert record.levelno == logging.WARNING

    # Test not suppress 'amqtt.broker' for others
    record = logging.LogRecord(
        name="amqtt.broker",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="No more test data",
        args=None,
        exc_info=None,
    )
    assert amqtt_filter.filter(record)
    assert record.levelno == logging.ERROR


def test_sanitize_filter() -> None:
    sanitize_filter = SanitizeFilter()

    # Test that it removes sensitive data in dict
    record = logging.LogRecord(
        name="some_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args={"auth": "secret", "email": "user@example.com", "notes": {"auth": "secret", "email": "user@example.com"}},
        exc_info=None,
    )
    assert sanitize_filter.filter(record)
    assert record.args == {"auth": "[REMOVED]", "email": "[REMOVED]", "notes": {"auth": "[REMOVED]", "email": "[REMOVED]"}}

    # Test that it doesn't remove non-sensitive data
    record = logging.LogRecord(
        name="some_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args={"name": "John Doe", "age": 30},
        exc_info=None,
    )
    assert sanitize_filter.filter(record)
    assert record.args == {"name": "John Doe", "age": 30}

    # Test that it removes sensitive data in tuple
    record = logging.LogRecord(
        name="some_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args=("email", "user@example.com"),
        exc_info=None,
    )
    assert sanitize_filter.filter(record)
    assert record.args == ("[REMOVED]", "[REMOVED]")
