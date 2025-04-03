"""LogHelper module."""

import copy
import logging
import sys
from typing import Any

import coloredlogs

from bumper.utils.settings import config as bumper_isc


class LogHelper:
    """LogHelper."""

    def __init__(self) -> None:
        """Log Helper init."""
        logger_name_size = self._clean_logs()
        # configure logger for requested verbosity
        log_format: str = "%(message)s"
        if bumper_isc.bumper_verbose == 2:
            log_format = f"[%(asctime)s] %(levelname)-5s :: %(name)-{logger_name_size}s - %(message)s"
        elif bumper_isc.bumper_verbose == 1:
            log_format = "[%(asctime)s] - %(message)s"

        self._clean_logs()
        root_logger = logging.getLogger("root")
        root_logger.setLevel(logging.getLevelName(bumper_isc.bumper_level))

        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setFormatter(logging.Formatter(log_format))
        root_handler.removeFilter(SanitizeFilter())
        root_handler.addFilter(SanitizeFilter())

        # root_logger.addHandler(root_handler)

        # add colored logs
        coloredlogs.install(
            level=logging.getLevelName(bumper_isc.bumper_level),
            fmt=log_format,
            logger=root_logger,
            stream=sys.stdout,
        )

    def _clean_logs(self) -> int:
        logger_name_size = 4
        for logger_name in [logging.getLogger()] + [logging.getLogger(name) for name in logging.getLogger().manager.loggerDict]:
            for handler in logger_name.handlers:
                logger_name.removeHandler(handler)
            # for filter in logger_name.filters:
            #     logger_name.removeFilter(filter)

            if bumper_isc.bumper_level == "INFO" and logger_name.name.startswith("aiohttp.access"):
                logger_name.setLevel(logging.DEBUG)
                logger_name.addFilter(AioHttpFilter())

            if bumper_isc.bumper_level == "INFO" and logger_name.name.startswith("httpx"):
                logger_name.setLevel(logging.WARNING)
            if bumper_isc.bumper_level == "INFO" and logger_name.name.startswith("amqtt"):
                logger_name.setLevel(logging.WARNING)
            if bumper_isc.bumper_level == "INFO" and logger_name.name.startswith("transitions.core"):
                logger_name.setLevel(logging.WARNING)

            logger_name_size = max(len(logger_name.name), logger_name_size)
        return logger_name_size + 1


class AioHttpFilter(logging.Filter):
    """AioHttpFilter."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Aio Http Filter filter."""
        if (
            record.name == "aiohttp.access" and record.levelno == logging.INFO
        ):  # Filters aiohttp.access log to switch it from INFO to DEBUG
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return bool(record.levelno == logging.DEBUG and logging.getLevelName(bumper_isc.bumper_level) == logging.DEBUG)


class SanitizeFilter(logging.Filter):
    """Filter to sensitive data."""

    # all lowercase
    _SANITIZE_LOG_KEYS: set[str] = {
        "auth",
        "did",
        "email",
        "login",
        "mobile",
        "token",
        "uid",
        "user",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record."""
        # The call signature matches string interpolation: args can be a tuple or a dict
        if isinstance(record.args, dict):
            record.args = self._sanitize_data(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(self._sanitize_data(value) for value in record.args)

        return True

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data (remove personal data)."""
        if isinstance(data, set | list):
            return [self._sanitize_data(entry) for entry in data]

        # NOTE: do be done as it will remove everything and not only the secret when loop above for tuple
        if isinstance(data, str) and any(substring in data.lower() for substring in self._SANITIZE_LOG_KEYS):
            return "[REMOVED]"

        if not isinstance(data, dict):
            return data

        sanitized_data = None
        for key, value in data.items():
            if any(substring in key.lower() for substring in self._SANITIZE_LOG_KEYS):
                if sanitized_data is None:
                    sanitized_data = copy.deepcopy(data)
                sanitized_data[key] = "[REMOVED]"
            elif isinstance(value, set | list | dict):
                if sanitized_data is None:
                    sanitized_data = copy.deepcopy(data)
                sanitized_data[key] = self._sanitize_data(value)

        return sanitized_data if sanitized_data else data
