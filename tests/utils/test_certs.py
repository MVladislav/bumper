"""Tests for certificate generation module."""

import datetime
import stat
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from bumper.utils.certs import (
    CA_VALIDITY_DAYS,
    SERVER_VALIDITY_DAYS,
    SUBJECT_ALT_NAMES,
    _create_ca_certificate,
    _create_server_certificate,
    _generate_ec_key,
    _parse_san_list,
    _write_cert,
    _write_key,
    generate_certificates,
)


class TestGenerateEcKey:
    def test_generates_ec_key(self) -> None:
        key = _generate_ec_key()
        assert isinstance(key, ec.EllipticCurvePrivateKey)

    def test_uses_secp256r1_curve(self) -> None:
        key = _generate_ec_key()
        assert isinstance(key.curve, ec.SECP256R1)

    def test_generates_unique_keys(self) -> None:
        key1 = _generate_ec_key()
        key2 = _generate_ec_key()
        key1_bytes = key1.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key2_bytes = key2.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        assert key1_bytes != key2_bytes


class TestParseSanList:
    def test_parses_ip_addresses(self) -> None:
        san_list = _parse_san_list()
        ip_sans = [san for san in san_list if isinstance(san, x509.IPAddress)]
        assert len(ip_sans) >= 1
        assert any(str(san.value) == "127.0.0.1" for san in ip_sans)

    def test_parses_dns_names(self) -> None:
        san_list = _parse_san_list()
        dns_sans = [san for san in san_list if isinstance(san, x509.DNSName)]
        assert len(dns_sans) > 100
        assert any(san.value == "localhost" for san in dns_sans)
        assert any(san.value == "*.ecouser.net" for san in dns_sans)
        assert any(san.value == "*.ecovacs.com" for san in dns_sans)

    def test_returns_correct_count(self) -> None:
        san_list = _parse_san_list()
        assert len(san_list) == len(SUBJECT_ALT_NAMES)


class TestCreateCaCertificate:
    def test_creates_valid_certificate(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        assert isinstance(cert, x509.Certificate)

    def test_certificate_subject(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert org == "ecovacs"
        assert cn == "ECOVACS CA"

    def test_certificate_is_self_signed(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        assert cert.subject == cert.issuer

    def test_certificate_validity_period(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        validity = cert.not_valid_after_utc - cert.not_valid_before_utc
        expected_days = datetime.timedelta(days=CA_VALIDITY_DAYS)
        assert validity == expected_days

    def test_certificate_has_ca_basic_constraints(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.critical is True
        assert bc.value.ca is True

    def test_certificate_has_key_usage(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.critical is True
        assert ku.value.key_cert_sign is True
        assert ku.value.crl_sign is True
        assert ku.value.digital_signature is False

    def test_certificate_has_subject_key_identifier(self) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        ski = cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        assert ski is not None
        assert ski.critical is False


class TestCreateServerCertificate:
    @pytest.fixture
    def ca_key_and_cert(self) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
        ca_key = _generate_ec_key()
        ca_cert = _create_ca_certificate(ca_key)
        return ca_key, ca_cert

    def test_creates_valid_certificate(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        assert isinstance(cert, x509.Certificate)

    def test_certificate_subject(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert org == "ecovacs"
        assert cn == "*.ecouser.net"

    def test_certificate_issuer_matches_ca(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        assert cert.issuer == ca_cert.subject

    def test_certificate_validity_period(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        validity = cert.not_valid_after_utc - cert.not_valid_before_utc
        expected_days = datetime.timedelta(days=SERVER_VALIDITY_DAYS)
        assert validity == expected_days

    def test_certificate_has_key_usage(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.critical is True
        assert ku.value.digital_signature is True
        assert ku.value.key_cert_sign is False

    def test_certificate_has_extended_key_usage(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.SERVER_AUTH in eku.value

    def test_certificate_has_san(self, ca_key_and_cert: tuple[ec.EllipticCurvePrivateKey, x509.Certificate]) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_ec_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        assert san is not None
        assert len(san.value) == len(SUBJECT_ALT_NAMES)


class TestWriteKey:
    def test_writes_key_to_file(self, tmp_path: Path) -> None:
        key = _generate_ec_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        assert key_path.exists()

    def test_key_file_is_pem_format(self, tmp_path: Path) -> None:
        key = _generate_ec_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        content = key_path.read_text()
        assert content.startswith("-----BEGIN EC PRIVATE KEY-----")
        assert "-----END EC PRIVATE KEY-----" in content

    def test_key_file_has_restricted_permissions(self, tmp_path: Path) -> None:
        key = _generate_ec_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        file_stat = key_path.stat()
        assert file_stat.st_mode & 0o777 == 0o600


class TestWriteCert:
    def test_writes_cert_to_file(self, tmp_path: Path) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        cert_path = tmp_path / "test.crt"
        _write_cert(cert, cert_path)
        assert cert_path.exists()

    def test_cert_file_is_pem_format(self, tmp_path: Path) -> None:
        key = _generate_ec_key()
        cert = _create_ca_certificate(key)
        cert_path = tmp_path / "test.crt"
        _write_cert(cert, cert_path)
        content = cert_path.read_text()
        assert content.startswith("-----BEGIN CERTIFICATE-----")
        assert "-----END CERTIFICATE-----" in content


class TestGenerateCertificates:
    def test_generates_all_files(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "certs"
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"

        result = generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        assert result is True
        assert ca_cert_path.exists()
        assert server_cert_path.exists()
        assert server_key_path.exists()
        assert (certs_dir / "ca.key").exists()
        assert (certs_dir / "ca.pem").exists()

    def test_skips_if_all_files_exist(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "certs"
        certs_dir.mkdir()
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"
        ca_key_path = certs_dir / "ca.key"

        # Create dummy files
        ca_cert_path.touch()
        server_cert_path.touch()
        server_key_path.touch()
        ca_key_path.touch()

        result = generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        assert result is False

    def test_generates_if_any_file_missing(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "certs"
        certs_dir.mkdir()
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"

        # Create only some files
        ca_cert_path.touch()
        server_cert_path.touch()

        result = generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        assert result is True

    def test_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "new" / "certs"
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"

        result = generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        assert result is True
        assert certs_dir.exists()

    def test_ca_pem_contains_all_components(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "certs"
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"

        generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        ca_pem_content = (certs_dir / "ca.pem").read_text()
        assert "-----BEGIN EC PRIVATE KEY-----" in ca_pem_content
        assert ca_pem_content.count("-----BEGIN CERTIFICATE-----") == 2

    def test_generated_certs_are_valid(self, tmp_path: Path) -> None:
        certs_dir = tmp_path / "certs"
        ca_cert_path = certs_dir / "ca.crt"
        server_cert_path = certs_dir / "bumper.crt"
        server_key_path = certs_dir / "bumper.key"

        generate_certificates(certs_dir, ca_cert_path, server_cert_path, server_key_path)

        # Load and verify CA cert
        ca_cert_pem = ca_cert_path.read_bytes()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)
        assert ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "ECOVACS CA"

        # Load and verify server cert
        server_cert_pem = server_cert_path.read_bytes()
        server_cert = x509.load_pem_x509_certificate(server_cert_pem)
        assert server_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "*.ecouser.net"
        assert server_cert.issuer == ca_cert.subject

        # Load and verify server key
        server_key_pem = server_key_path.read_bytes()
        server_key = serialization.load_pem_private_key(server_key_pem, password=None)
        assert isinstance(server_key, ec.EllipticCurvePrivateKey)
