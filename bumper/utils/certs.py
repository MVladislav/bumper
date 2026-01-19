"""Certificate generation module for Bumper."""

import datetime
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_LOGGER = logging.getLogger(__name__)

# Subject Alternative Names for the server certificate
# Matches the extensive list from scripts/create-cert.sh
SUBJECT_ALT_NAMES: list[str] = [
    # IP addresses
    "IP:127.0.0.1",
    # DNS names
    "DNS:localhost",
    "DNS:*.a1zYhiMF5J3.iot-as-mqtt.cn-shanghai.aliyuncs.com",
    "DNS:*.eu-central-1.aliyuncs.com",
    "DNS:*.iot-as-mqtt.cn-shanghai.aliyuncs.com",
    "DNS:*.itls.eu-central-1.aliyuncs.com",
    "DNS:*.openaccount.aliyun.com",
    "DNS:*.aliyun.com",
    "DNS:*.aliyuncs.com",
    "DNS:*.api-app.dc-eu.ww.ecouser.net",
    "DNS:*.api-app.ww.ecouser.net",
    "DNS:*.api-base.dc-eu.ww.ecouser.net",
    "DNS:*.api-ngiot.dc-eu.ww.ecouser.net",
    "DNS:*.app.cn.ecouser.net",
    "DNS:*.app.ww.ecouser.net",
    "DNS:*.area.cn.ecouser.net",
    "DNS:*.area.robotcn.ecouser.net",
    "DNS:*.area.robotww.ecouser.net",
    "DNS:*.area.ww.ecouser.net",
    "DNS:*.as.dc.ww.ecouser.net",
    "DNS:*.autodiscover.ecovacs.com",
    "DNS:*.base.cn.ecouser.net",
    "DNS:*.base.ww.ecouser.net",
    "DNS:*.bizcn.ecouser.net",
    "DNS:*.bizww.ecouser.net",
    "DNS:*.ca.robotcn.ecouser.net",
    "DNS:*.ca.robotww.ecouser.net",
    "DNS:*.cfjump.ecovacs.com",
    "DNS:*.checkout-au.ecovacs.com",
    "DNS:*.checkout-test.ecovacs.com",
    "DNS:*.checkout-uk.ecovacs.com",
    "DNS:*.cloud-ui.dc-as.cloud.ww.ecouser.net",
    "DNS:*.cloud-ui.dc-cn.cloud.cn.ecouser.net",
    "DNS:*.cloud-ui.dc-eu.cloud.ww.ecouser.net",
    "DNS:*.cloud-ui.dc-na.cloud.ww.ecouser.net",
    "DNS:*.cloud.cn.ecouser.net",
    "DNS:*.cloud.ww.ecouser.net",
    "DNS:*.cn-shanghai.aliyuncs.com",
    "DNS:*.cn.dc.cn.ecouser.net",
    "DNS:*.cn.ecouser.net",
    "DNS:*.codepush-base.dc-na.ww.ecouser.net",
    "DNS:*.comingsoon.ecovacs.com",
    "DNS:*.czjquw.ecovacs.com",
    "DNS:*.dc-as.app.ww.ecouser.net",
    "DNS:*.dc-as.base.ww.ecouser.net",
    "DNS:*.dc-as.bizww.ecouser.net",
    "DNS:*.dc-as.cloud.ww.ecouser.net",
    "DNS:*.dc-as.ngiot.ww.ecouser.net",
    "DNS:*.dc-as.rapp.ww.ecouser.net",
    "DNS:*.dc-as.rop.ww.ecouser.net",
    "DNS:*.dc-as.ww.ecouser.net",
    "DNS:*.dc-aus.ww.ecouser.net",
    "DNS:*.dc-cn.app.cn.ecouser.net",
    "DNS:*.dc-cn.base.cn.ecouser.net",
    "DNS:*.dc-cn.bizcn.ecouser.net",
    "DNS:*.dc-cn.cloud.cn.ecouser.net",
    "DNS:*.dc-cn.cn.ecouser.net",
    "DNS:*.dc-cn.ngiot.cn.ecouser.net",
    "DNS:*.dc-cn.rapp.cn.ecouser.net",
    "DNS:*.dc-cn.rop.cn.ecouser.net",
    "DNS:*.dc-eu.app.ww.ecouser.net",
    "DNS:*.dc-eu.base.ww.ecouser.net",
    "DNS:*.dc-eu.bizww.ecouser.net",
    "DNS:*.dc-eu.cloud.ww.ecouser.net",
    "DNS:*.dc-eu.ngiot.ww.ecouser.net",
    "DNS:*.dc-eu.rapp.ww.ecouser.net",
    "DNS:*.dc-eu.rop.ww.ecouser.net",
    "DNS:*.dc-eu.ww.ecouser.net",
    "DNS:*.dc-hq.cn.ecouser.net",
    "DNS:*.dc-hq.devhq.ecouser.net",
    "DNS:*.dc-na.app.ww.ecouser.net",
    "DNS:*.dc-na.base.ww.ecouser.net",
    "DNS:*.dc-na.bizww.ecouser.net",
    "DNS:*.dc-na.cloud.ww.ecouser.net",
    "DNS:*.dc-na.ngiot.ww.ecouser.net",
    "DNS:*.dc-na.rapp.ww.ecouser.net",
    "DNS:*.dc-na.rop.ww.ecouser.net",
    "DNS:*.dc-na.ww.ecouser.net",
    "DNS:*.dc.cn.ecouser.net",
    "DNS:*.dc.ecouser.net",
    "DNS:*.dc.robotcn.ecouser.net",
    "DNS:*.dc.robotww.ecouser.net",
    "DNS:*.dc.ww.ecouser.net",
    "DNS:*.dev.ecouser.net",
    "DNS:*.devhq.ecouser.net",
    "DNS:*.dl.ecouser.net",
    "DNS:*.ecouser.net",
    "DNS:*.ecovacs.com",
    "DNS:*.eis-nlp.dc-eu.ww.ecouser.net",
    "DNS:*.eml.ecovacs.com",
    "DNS:*.eu.dc.ww.ecouser.net",
    "DNS:*.exchange.ecovacs.com",
    "DNS:*.gl-de-api.ecovacs.com",
    "DNS:*.gl-de-openapi.ecovacs.com",
    "DNS:*.gl-us-pub.ecovacs.com",
    "DNS:*.jmq-ngiot-eu.dc.robotww.ecouser.net",
    "DNS:*.lb.ecouser.net",
    "DNS:*.lbo.ecouser.net",
    "DNS:*.mail.ecovacs.com",
    "DNS:*.mpush-api.aliyun.com",
    "DNS:*.msg-eu.ecouser.net",
    "DNS:*.na.dc.ww.ecouser.net",
    "DNS:*.ngiot.cn.ecouser.net",
    "DNS:*.ngiot.ww.ecouser.net",
    "DNS:*.parts-apac.ecovacs.com",
    "DNS:*.portal-ww-qa.ecouser.net",
    "DNS:*.portal-ww-qa1.ecouser.net",
    "DNS:*.portal-ww.ecouser.net",
    "DNS:*.qdbdrg.ecovacs.com",
    "DNS:*.rapp.cn.ecouser.net",
    "DNS:*.rapp.ww.ecouser.net",
    "DNS:*.recommender.ecovacs.com",
    "DNS:*.robotcn.ecouser.net",
    "DNS:*.robotww.ecouser.net",
    "DNS:*.rop.cn.ecouser.net",
    "DNS:*.rop.ww.ecouser.net",
    "DNS:*.sa-eu-datasink.ecovacs.com",
    "DNS:*.sdk.openaccount.aliyun.com",
    "DNS:*.site-static.ecovacs.com",
    "DNS:*.store-de.ecovacs.com",
    "DNS:*.store-fr.ecovacs.com",
    "DNS:*.store-it.ecovacs.com",
    "DNS:*.store-jp.ecovacs.com",
    "DNS:*.store-uk.ecovacs.com",
    "DNS:*.storehk.ecovacs.com",
    "DNS:*.storesg.ecovacs.com",
    "DNS:*.users-base.dc-eu.ww.ecouser.net",
    "DNS:*.usshop.ecovacs.com",
    "DNS:*.vpn.ecovacs.com",
    "DNS:*.ww.ecouser.net",
    "DNS:*.www.ecouser.net",
    "DNS:*.www.eml.ecovacs.com",
    "DNS:aliyun.com",
    "DNS:aliyuncs.com",
    "DNS:ecouser.net",
    "DNS:ecovacs.com",
]

# Certificate validity periods (in days) matching create-cert.sh
CA_VALIDITY_DAYS = 6669
SERVER_VALIDITY_DAYS = 666


def _generate_ec_key() -> ec.EllipticCurvePrivateKey:
    """Generate an EC private key using prime256v1 curve."""
    return ec.generate_private_key(ec.SECP256R1())


def _parse_san_list() -> list[x509.GeneralName]:
    """Parse the SAN list into x509 GeneralName objects."""
    general_names: list[x509.GeneralName] = []
    for san in SUBJECT_ALT_NAMES:
        if san.startswith("IP:"):
            from ipaddress import ip_address

            general_names.append(x509.IPAddress(ip_address(san[3:])))
        elif san.startswith("DNS:"):
            general_names.append(x509.DNSName(san[4:]))
    return general_names


def _create_ca_certificate(ca_key: ec.EllipticCurvePrivateKey) -> x509.Certificate:
    """Create a CA certificate."""
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ecovacs"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ECOVACS CA"),
    ])

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CA_VALIDITY_DAYS))
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
    return cert


def _create_server_certificate(
    server_key: ec.EllipticCurvePrivateKey,
    ca_key: ec.EllipticCurvePrivateKey,
    ca_cert: x509.Certificate,
) -> x509.Certificate:
    """Create a server certificate signed by the CA."""
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ecovacs"),
        x509.NameAttribute(NameOID.COMMON_NAME, "*.ecouser.net"),
    ])

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=SERVER_VALIDITY_DAYS))
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
    return cert


def _write_key(key: ec.EllipticCurvePrivateKey, path: Path) -> None:
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


def generate_certificates(certs_dir: Path, ca_cert_path: Path, server_cert_path: Path, server_key_path: Path) -> bool:
    """Generate CA and server certificates if they don't exist.

    Args:
        certs_dir: Directory to store certificates
        ca_cert_path: Path for CA certificate
        server_cert_path: Path for server certificate
        server_key_path: Path for server private key

    Returns:
        True if certificates were generated, False if they already existed

    """
    # Check if all required certificates exist
    ca_key_path = certs_dir / "ca.key"
    ca_pem_path = certs_dir / "ca.pem"

    if ca_cert_path.exists() and ca_key_path.exists() and server_cert_path.exists() and server_key_path.exists():
        _LOGGER.debug("All certificate files already exist, skipping generation")
        return False

    _LOGGER.info("Generating certificates in %s", certs_dir)
    certs_dir.mkdir(parents=True, exist_ok=True)

    # Generate CA certificate
    _LOGGER.info("Creating CA certificate...")
    ca_key = _generate_ec_key()
    ca_cert = _create_ca_certificate(ca_key)
    _write_key(ca_key, ca_key_path)
    _write_cert(ca_cert, ca_cert_path)

    # Generate server certificate
    _LOGGER.info("Creating server certificate...")
    server_key = _generate_ec_key()
    server_cert = _create_server_certificate(server_key, ca_key, ca_cert)
    _write_key(server_key, server_key_path)
    _write_cert(server_cert, server_cert_path)

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

    _LOGGER.info("Certificates created successfully in %s", certs_dir)
    return True
