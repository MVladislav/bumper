"""Unit tests for `init` of `bumper.main` arguments handling and correct startup/shutdown invocation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import bumper
from bumper import utils
from bumper.utils.settings import config as bumper_isc
from tests import BUMPER_LISTEN


@patch("bumper.shutdown")
@patch("bumper.start")
@pytest.mark.parametrize(
    ("cmd_args", "expected_level", "expected_verbose", "expected_listen", "expected_announce"),
    [
        (["--debug_level", "DEBUG"], "DEBUG", None, None, None),
        (["--debug_verbose", "3"], None, 3, None, None),
        (["--listen", "127.0.0.1"], None, None, "127.0.0.1", None),
        (["--announce", "127.0.0.1"], None, None, None, "127.0.0.1"),
        (["--debug_level", "DEBUG", "--listen", "127.0.0.1", "--announce", "127.0.0.1"], "DEBUG", None, "127.0.0.1", "127.0.0.1"),
    ],
)
def test_args_parse(
    mock_start: MagicMock,
    mock_shutdown: MagicMock,
    cmd_args: list[str],
    expected_level: str | None,
    expected_verbose: int | None,
    expected_listen: str | None,
    expected_announce: str | None,
    test_files: dict[str, Path],
) -> None:
    """Verify that CLI arguments properly set configuration and invoke start/shutdown."""
    # Set certificate paths
    bumper_isc.ca_cert = test_files["certs"] / "ca.crt"
    bumper_isc.server_cert = test_files["certs"] / "bumper.crt"
    bumper_isc.server_key = test_files["certs"] / "bumper.key"

    bumper.main(cmd_args)

    if expected_level is not None:
        assert bumper_isc.debug_bumper_level == expected_level
    if expected_verbose is not None:
        assert bumper_isc.debug_bumper_verbose == expected_verbose
    if expected_listen is not None:
        assert bumper_isc.bumper_listen == expected_listen
    if expected_announce is not None:
        assert bumper_isc.bumper_announce_ip == expected_announce

    mock_start.assert_called_once()
    mock_shutdown.assert_called_once()


@patch("bumper.shutdown")
@patch("bumper.start")
def test_args_parse_listen_none(
    mock_start: MagicMock,
    mock_shutdown: MagicMock,
) -> None:
    """Ensure passing None to --listen disables startup and triggers shutdown only."""
    bumper.main(["--listen", None])
    assert not utils.is_valid_ip(bumper_isc.bumper_listen)

    mock_start.assert_not_called()
    mock_shutdown.assert_called_once()

    # Reset listen for other tests
    bumper_isc.bumper_listen = BUMPER_LISTEN
