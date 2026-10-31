"""Tests for bumper/utils/device_errors.py"""

from bumper.utils.device_errors import DEVICE_ERRORS, DEVICE_ERRORS_BY_CODE, describe, recommendation


def test_the_error_the_robot_reports_the_often() -> None:
    """The codes the robot uses the most are known."""
    assert describe(109) == "Roller abnormal (109)"
    assert describe(312) == "Auto empty station: dust bag full (312)"
    assert describe(520, include_code=False) == "Trapped"


def test_no_error() -> None:
    """The code that means everything is fine."""
    assert describe(0) == "No error (0)"


def test_an_unknown_code_is_kept() -> None:
    """A code the robot does not use is not lost."""
    assert describe(9999) == "Unknown error (9999)"
    assert describe(9999, include_code=False) == "Unknown error"


def test_no_code_at_all() -> None:
    """Without a code there is nothing to say."""
    assert describe(None) == ""


def test_every_code_is_known_once() -> None:
    """Every error has a number of its own."""
    codes = [error.code for error in DEVICE_ERRORS_BY_CODE.values()]
    assert codes == sorted(codes)
    assert len(codes) == len(set(codes))


def test_every_known_error_has_a_next_step() -> None:
    """Known errors always have either specific or safe fallback guidance."""
    assert all(recommendation(error.code) for error in DEVICE_ERRORS)
    assert "obstruction" in recommendation(520)
    assert "model-specific" in recommendation(9999)
