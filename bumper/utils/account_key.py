"""The key the app encrypts account fields with.

The app reads the public half from the API and encrypts an address or a
password with it before it leaves the device. The private half lives in the
data directory, so this server can read those fields and no other server
can.
"""

import base64
import os
from pathlib import Path
import threading

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from bumper.utils.settings import config as bumper_isc

_LOCK = threading.Lock()
_KEY_SIZE = 2048
_PUBLIC_EXPONENT = 65537


def account_public_key() -> str:
    """Return the public half of the account key as base64 DER."""
    key = _load_or_create(bumper_isc.account_key_file)
    der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(der).decode("ascii")


def decrypt_account_field(value: str) -> str | None:
    """Read a field the app encrypted with the account key.

    Answers None when the value is empty or was not encrypted with the key
    this server holds.
    """
    if not value:
        return None
    try:
        ciphertext = base64.b64decode(value.replace(" ", "+"), validate=True)
        plaintext = _load_or_create(bumper_isc.account_key_file).decrypt(ciphertext, padding.PKCS1v15())
        return plaintext.decode("utf-8").strip()
    except ValueError:
        return None


def _load_or_create(path: Path) -> rsa.RSAPrivateKey:
    """Return the account key, generating and storing it on first use."""
    with _LOCK:
        try:
            return _read_key(path)
        except FileNotFoundError:
            key = rsa.generate_private_key(public_exponent=_PUBLIC_EXPONENT, key_size=_KEY_SIZE)
            try:
                _write_key(path, key)
            except FileExistsError:
                return _read_key(path)
            return key


def _read_key(path: Path) -> rsa.RSAPrivateKey:
    """Read the account key from the path."""
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        msg = f"{path} does not hold an RSA private key"
        raise TypeError(msg)
    return key


def _write_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    """Store the account key where only its owner can read it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
