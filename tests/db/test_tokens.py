from typing import TYPE_CHECKING, Any

import pytest

from bumper.db import token_repo
from bumper.utils.settings import config as bumper_isc

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


@pytest.mark.usefixtures("clean_database")
def test_get_valid_by_secret_finds_every_field() -> None:
    """A secret is looked up as the portal token, the auth code, or the IT token."""
    token_repo.add("user", "portal-token")
    token_repo.add_auth_code("user", "auth-code")
    token_repo.add_it_token("user", "it-token")

    for secret in ("portal-token", "auth-code", "it-token"):
        token = token_repo.get_valid_by_secret(secret)
        assert token is not None
        assert token.userid == "user"

    assert token_repo.get_valid_by_secret("missing") is None
    assert token_repo.get_valid_by_secret("") is None


@pytest.mark.usefixtures("clean_database")
def test_get_valid_by_secret_ignores_an_expired_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """An expired token row is not a usable secret."""
    monkeypatch.setattr(bumper_isc, "TOKEN_VALIDITY_SECONDS", -1)
    token_repo.add("user", "expired")

    assert token_repo.get_by_secret("expired") is not None
    assert token_repo.get_valid_by_secret("expired") is None


@pytest.mark.usefixtures("clean_database")
def test_reassign_user_moves_token_without_target_row() -> None:
    """A merged account keeps its only token under the remaining user."""
    token_repo.add("legacy", "legacy-token")
    token_repo.add_auth_code("legacy", "legacy-auth")

    token_repo.reassign_user("legacy", "canonical")

    assert token_repo.list_for_user("legacy") == []
    tokens = token_repo.list_for_user("canonical")
    assert len(tokens) == 1
    assert tokens[0].token == "legacy-token"  # noqa: S105
    assert tokens[0].auth_code == "legacy-auth"


@pytest.mark.usefixtures("clean_database")
def test_reassign_user_keeps_both_tokens() -> None:
    """A merged account keeps the token and auth code of both records."""
    token_repo.add("canonical", "canonical-token")
    token_repo.add("legacy", "legacy-token")
    token_repo.add_auth_code("legacy", "legacy-auth")

    token_repo.reassign_user("legacy", "canonical")

    assert token_repo.list_for_user("legacy") == []
    tokens = {token.token: token for token in token_repo.list_for_user("canonical")}
    assert set(tokens) == {"canonical-token", "legacy-token"}
    assert tokens["legacy-token"].auth_code == "legacy-auth"
    assert token_repo.verify_auth_code("canonical", "legacy-auth")


@pytest.mark.usefixtures("clean_database")
def test_auth_code_is_attached_to_the_named_token_row() -> None:
    """An auth code belongs to the client that asked for it."""
    token_repo.add("user", "first-token")
    token_repo.add("user", "second-token")

    assert token_repo.add_auth_code_to_token("second-token", "second-auth")

    assert token_repo.get_by_token("first-token").auth_code is None
    assert token_repo.get_by_token("second-token").auth_code == "second-auth"


@pytest.mark.usefixtures("clean_database")
def test_login_by_it_token_rejects_an_expired_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """An IT token of an expired login cannot start a session."""
    monkeypatch.setattr(bumper_isc, "TOKEN_VALIDITY_SECONDS", -1)
    token_repo.add("user", "portal-token")
    token_repo.add_it_token("user", "it-token")

    assert token_repo.get_by_it_token("it-token") is not None
    assert token_repo.login_by_it_token("it-token") is None
