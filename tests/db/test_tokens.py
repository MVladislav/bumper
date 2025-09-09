from typing import TYPE_CHECKING, Any

import pytest

from bumper.db import token_repo

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.parametrize(
    ("method_name", "args", "expected"),
    [
        ("get_by_auth_code", ["non_existing_auth_code"], None),
        ("add_auth_code", ["nonexistent_user", "auth_code_999"], False),
        ("add_it_token", ["nonexistent_user", "it_token_999"], False),
        ("verify_it", ["nonexistent_user", "nonexistent_it_token"], False),
    ],
)
@pytest.mark.usefixtures("clean_database")
def test_token_negative_cases(method_name: str, args: list[Any], expected: Any) -> None:
    method: Callable[..., Any] = getattr(token_repo, method_name)
    result = method(*args)
    assert result == expected
