"""Tests for the key the app encrypts account fields with."""

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import pytest

from bumper.utils.account_key import account_public_key, decrypt_account_field
from bumper.utils.settings import config as bumper_isc


def test_the_key_is_stored_once_and_reads_what_the_app_encrypts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The key lives in a file only its owner can read and survives a reload."""
    key_file = tmp_path / "account.key"
    monkeypatch.setattr(bumper_isc, "account_key_file", key_file)

    public = account_public_key()
    assert key_file.is_file()
    assert key_file.stat().st_mode & 0o777 == 0o600
    assert account_public_key() == public

    public_key = serialization.load_der_public_key(base64.b64decode(public))
    assert isinstance(public_key, rsa.RSAPublicKey)
    ciphertext = public_key.encrypt(b"new@example.com", padding.PKCS1v15())
    assert decrypt_account_field(base64.b64encode(ciphertext).decode("ascii")) == "new@example.com"


def test_a_value_from_another_key_is_not_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A field that was not encrypted for this server is answered as unread."""
    monkeypatch.setattr(bumper_isc, "account_key_file", tmp_path / "account.key")
    account_public_key()

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ciphertext = other_key.public_key().encrypt(b"new@example.com", padding.PKCS1v15())
    assert decrypt_account_field(base64.b64encode(ciphertext).decode("ascii")) is None
    assert decrypt_account_field("not base64") is None
    assert decrypt_account_field("") is None
