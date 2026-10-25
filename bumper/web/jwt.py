"""The token of the app.

The app sends its token as a bearer token, and the claims carry the user, the
client and the auth code. A token that Bumper issued can be checked against the
certificate of the TLS server, which carries the public part of the signing key.
"""

from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa
import jwt

from bumper.utils.settings import config as bumper_isc


def get_jwt_details(auth_header: str | None) -> dict[str, Any] | None:
    """Extract the claims of the bearer token of a request."""
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return extract_jwt_details(token.strip())


def extract_jwt_details(token: str | None) -> dict[str, Any] | None:
    """Extract the claims of a token without checking its signature."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        return None
    return _details(payload)


def verify_jwt(token: str | None, *, token_type: str = "a") -> dict[str, Any] | None:  # noqa: S107
    """Return the claims of a token Bumper signed and that is still valid.

    The token has to carry the expected type, so a refresh token cannot stand in
    for an access token. The signature is checked with the certificate of the
    TLS server, which carries the public part of the key that signed the token.
    """
    if token is None:
        return None
    try:
        certificate = x509.load_pem_x509_certificate(bumper_isc.server_cert.read_bytes())
        public_key = certificate.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey | ec.EllipticCurvePublicKey):
            return None
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[bumper_isc.TOKEN_JWT_ALG],
            options={"require": ["exp"]},
        )
    except (OSError, ValueError, jwt.PyJWTError):
        return None
    if payload.get("t") != token_type:
        return None
    return _details(payload)


def _details(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the claims of a token in the shape the server reads."""
    return {
        "issued_at": payload.get("iat"),
        "expires_at": payload.get("exp"),
        "client_id": payload.get("c"),
        "user_id": payload.get("u"),
        "client_resource": payload.get("r"),
        "auth_code": payload.get("ac"),
    }
