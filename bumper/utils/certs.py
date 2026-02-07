"""Certificate generation module for Bumper."""

from collections import defaultdict
import datetime
from ipaddress import ip_address
import logging
from pathlib import Path
from typing import Any, Literal

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from bumper.utils.settings import config as bumper_isc

_LOGGER = logging.getLogger(__name__)

# Raw domain list for certificate SANs
# These are processed to generate wildcard entries covering all subdomains
RAW_DOMAINS: list[str] = [
    # Aliyun domains
    "a1zYhiMF5J3.iot-as-mqtt.cn-shanghai.aliyuncs.com",
    "mpush-api.aliyun.com",
    "sdk.openaccount.aliyun.com",
    "itls.eu-central-1.aliyuncs.com",
    "eu-central-1.aliyuncs.com",
    # Ecovacs robot domains
    "ca.robotww.ecouser.net",
    "ca.robotcn.ecouser.net",
    "robotcn.ecouser.net",
    "dc.robotcn.ecouser.net",
    "area.robotww.ecouser.net",
    "area.robotcn.ecouser.net",
    # Ecovacs.com domains
    "autodiscover.ecovacs.com",
    "cfjump.ecovacs.com",
    "checkout-au.ecovacs.com",
    "checkout-test.ecovacs.com",
    "checkout-uk.ecovacs.com",
    "comingsoon.ecovacs.com",
    "czjquw.ecovacs.com",
    "ecovacs.com",
    "eml.ecovacs.com",
    "www.eml.ecovacs.com",
    "exchange.ecovacs.com",
    "gl-de-api.ecovacs.com",
    "gl-de-openapi.ecovacs.com",
    "gl-us-pub.ecovacs.com",
    "mail.ecovacs.com",
    "parts-apac.ecovacs.com",
    "qdbdrg.ecovacs.com",
    "recommender.ecovacs.com",
    "sa-eu-datasink.ecovacs.com",
    "site-static.ecovacs.com",
    "store-de.ecovacs.com",
    "store-fr.ecovacs.com",
    "storehk.ecovacs.com",
    "store-it.ecovacs.com",
    "store-jp.ecovacs.com",
    "storesg.ecovacs.com",
    "store-uk.ecovacs.com",
    "usshop.ecovacs.com",
    "vpn.ecovacs.com",
    # Ecouser.net China domains
    "dc-cn.bizcn.ecouser.net",
    "dc-as.bizww.ecouser.net",
    "dc-eu.bizww.ecouser.net",
    "dc-na.bizww.ecouser.net",
    "dc-cn.app.cn.ecouser.net",
    "area.cn.ecouser.net",
    "dc-cn.base.cn.ecouser.net",
    "cloud-ui.dc-cn.cloud.cn.ecouser.net",
    "dc-cn.cloud.cn.ecouser.net",
    "cn.ecouser.net",
    "cn.dc.cn.ecouser.net",
    "dc-cn.cn.ecouser.net",
    "dc.cn.ecouser.net",
    "dc-hq.cn.ecouser.net",
    "dc-cn.ngiot.cn.ecouser.net",
    "dc-cn.rapp.cn.ecouser.net",
    "dc-cn.rop.cn.ecouser.net",
    # Ecouser.net general domains
    "dc.ecouser.net",
    "dev.ecouser.net",
    "dc-hq.devhq.ecouser.net",
    "dl.ecouser.net",
    "ecouser.net",
    "lb.ecouser.net",
    "lbo.ecouser.net",
    "msg-eu.ecouser.net",
    "portal-ww.ecouser.net",
    "portal-ww-qa1.ecouser.net",
    "portal-ww-qa.ecouser.net",
    "jmq-ngiot-eu.dc.robotww.ecouser.net",
    # Ecouser.net worldwide domains
    "api-app.ww.ecouser.net",
    "dc-as.app.ww.ecouser.net",
    "dc-eu.app.ww.ecouser.net",
    "dc-na.app.ww.ecouser.net",
    "area.ww.ecouser.net",
    "dc-as.base.ww.ecouser.net",
    "dc-eu.base.ww.ecouser.net",
    "dc-na.base.ww.ecouser.net",
    "cloud-ui.dc-as.cloud.ww.ecouser.net",
    "dc-as.cloud.ww.ecouser.net",
    "cloud-ui.dc-eu.cloud.ww.ecouser.net",
    "dc-eu.cloud.ww.ecouser.net",
    "cloud-ui.dc-na.cloud.ww.ecouser.net",
    "dc-na.cloud.ww.ecouser.net",
    "as.dc.ww.ecouser.net",
    "dc-as.ww.ecouser.net",
    "dc-aus.ww.ecouser.net",
    "dc.ww.ecouser.net",
    "api-app.dc-eu.ww.ecouser.net",
    "api-base.dc-eu.ww.ecouser.net",
    "api-ngiot.dc-eu.ww.ecouser.net",
    "dc-eu.ww.ecouser.net",
    "eis-nlp.dc-eu.ww.ecouser.net",
    "eu.dc.ww.ecouser.net",
    "users-base.dc-eu.ww.ecouser.net",
    "codepush-base.dc-na.ww.ecouser.net",
    "dc-na.ww.ecouser.net",
    "na.dc.ww.ecouser.net",
    "dc-as.ngiot.ww.ecouser.net",
    "dc-eu.ngiot.ww.ecouser.net",
    "dc-na.ngiot.ww.ecouser.net",
    "dc-as.rapp.ww.ecouser.net",
    "dc-eu.rapp.ww.ecouser.net",
    "dc-na.rapp.ww.ecouser.net",
    "dc-as.rop.ww.ecouser.net",
    "dc-eu.rop.ww.ecouser.net",
    "dc-na.rop.ww.ecouser.net",
    "ww.ecouser.net",
    "www.ecouser.net",
]


def _build_domain_tree(domains: list[str]) -> dict[str, Any]:
    """Build a hierarchical tree structure from domain list.

    Args:
        domains: List of domain names

    Returns:
        Dictionary tree where keys are root domains (e.g., ecovacs.com)
        and values are nested dicts of subdomains

    """
    tree: dict[str, Any] = defaultdict(lambda: defaultdict(dict))

    for domain in domains:
        parts = domain.split(".")
        if len(parts) < 2:
            continue
        root = ".".join(parts[-2:])  # e.g., ecovacs.com
        subparts = parts[:-2]  # subdomains before the root
        current = tree[root]
        for part in reversed(subparts):
            current = current.setdefault(part, {})

    return tree


def _generate_wildcards(wildcard_set: set[str], node: dict[str, Any], parent_parts: list[str]) -> None:
    """Recursively generate wildcard entries from domain tree.

    Args:
        wildcard_set: Set to add wildcard entries to
        node: Current node in domain tree
        parent_parts: List of parent domain parts

    """
    if not node:
        # No children, wildcard parent
        if parent_parts:
            wildcard = "*." + ".".join(parent_parts)
            wildcard_set.add(wildcard)
        return

    # Node has children - add wildcard for this level
    if parent_parts:
        wildcard = "*." + ".".join(parent_parts)
        wildcard_set.add(wildcard)

    # Recurse into children
    for child, child_node in node.items():
        _generate_wildcards(wildcard_set, child_node, [child, *parent_parts])


def _build_san_list() -> list[str]:
    """Build the complete SAN list from raw domains.

    Returns:
        List of SAN entries including IP addresses, localhost, and wildcard domains

    """
    san_list: list[str] = [
        "IP:127.0.0.1",
        "DNS:localhost",
    ]

    # Build domain tree and generate wildcards
    tree = _build_domain_tree(RAW_DOMAINS)
    wildcard_set: set[str] = set()

    for root in tree:
        # Always include root domain itself
        wildcard_set.add(root)
        # Generate wildcards for all subdomains
        _generate_wildcards(wildcard_set, tree[root], [root])

    # Add all wildcard entries as DNS SANs
    san_list.extend(f"DNS:{entry}" for entry in sorted(wildcard_set))
    return san_list


def _generate_key(key_type: Literal["ec", "rsa"] = "ec") -> ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey:
    """Generate private key based on type."""
    key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None = None
    if key_type == "rsa":
        if not 2048 <= bumper_isc.cert_rsa_key_size <= 4096:
            msg = "RSA key size must be between 2048-4096 bits"
            raise ValueError(msg)
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=bumper_isc.cert_rsa_key_size,
        )
    else:  # ec
        key = ec.generate_private_key(ec.SECP256R1())

    return key


def _parse_san_list() -> list[x509.GeneralName]:
    """Parse the SAN list into x509 GeneralName objects."""
    general_names: list[x509.GeneralName] = []
    for san in _build_san_list():
        if san.startswith("IP:"):
            general_names.append(x509.IPAddress(ip_address(san[3:])))
        elif san.startswith("DNS:"):
            general_names.append(x509.DNSName(san[4:]))
    return general_names


def _create_ca_certificate(ca_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey) -> x509.Certificate:
    """Create a CA certificate."""
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ecovacs"),
            x509.NameAttribute(NameOID.COMMON_NAME, "ECOVACS CA"),
        ],
    )

    now = datetime.datetime.now(datetime.UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=bumper_isc.ca_valid_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )


def _create_server_certificate(
    server_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey,
    ca_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
) -> x509.Certificate:
    """Create a server certificate signed by the CA."""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ecovacs"),
            x509.NameAttribute(NameOID.COMMON_NAME, "*.ecouser.net"),
        ],
    )

    now = datetime.datetime.now(datetime.UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=bumper_isc.server_valid_days))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(_parse_san_list()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )


def _write_key(key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey, path: Path) -> None:
    """Write a private key to a file with restricted permissions."""
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(key_bytes)
    path.chmod(0o600)


def _write_cert(cert: x509.Certificate, path: Path) -> None:
    """Write a certificate to a file."""
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    path.write_bytes(cert_bytes)


def generate_certificates() -> bool:
    """Generate CA and server certificates if they don't exist.

    Returns:
        True if certificates were generated, False if they already existed

    """
    if bumper_isc.cert_key_type not in ["ec", "rsa"]:
        msg = "Wrong Certificate Key Type provided"
        raise ValueError(msg)

    ca_pem_path = bumper_isc.certs_dir / "ca.pem"
    ca_cert_bump = bumper_isc.ca_cert
    ca_key_bump = bumper_isc.ca_key
    server_cert_bump = bumper_isc.server_cert
    server_key_bump = bumper_isc.server_key

    # Create unique identifier from parent directories only
    parent_dirs = {ca_pem_path.parent, ca_cert_bump.parent, ca_key_bump.parent, server_cert_bump.parent, server_key_bump.parent}
    paths_info = ", ".join(str(p) for p in sorted(parent_dirs))

    # Check if all required certificates exist
    if all(p.exists() for p in [ca_cert_bump, server_cert_bump, server_key_bump]):
        _LOGGER.debug("All certificate files already exist, skipping generation")
        return False

    _LOGGER.info(f"Generating {bumper_isc.cert_key_type.upper()} certificates in directories: {paths_info}")

    # Create all parent directories
    for parent_dir in sorted(parent_dirs):
        parent_dir.mkdir(parents=True, exist_ok=True)

    # Generate CA certificate
    _LOGGER.info("Creating CA certificate...")
    ca_key = _generate_key(bumper_isc.cert_key_type)
    ca_cert = _create_ca_certificate(ca_key)
    _write_key(ca_key, ca_key_bump)
    _write_cert(ca_cert, ca_cert_bump)

    # Generate server certificate
    _LOGGER.info("Creating server certificate...")
    server_key = _generate_key(bumper_isc.cert_key_type)
    server_cert = _create_server_certificate(server_key, ca_key, ca_cert)
    _write_key(server_key, server_key_bump)
    _write_cert(server_cert, server_cert_bump)

    # Create combined ca.pem (server key + server cert + CA cert)
    _LOGGER.info("Creating combined ca.pem...")
    server_key_bytes = server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    server_cert_bytes = server_cert.public_bytes(serialization.Encoding.PEM)
    ca_cert_bytes = ca_cert.public_bytes(serialization.Encoding.PEM)
    ca_pem_path.write_bytes(server_key_bytes + server_cert_bytes + ca_cert_bytes)

    _LOGGER.info(f"{bumper_isc.cert_key_type.upper()} certificates created successfully")
    return True
