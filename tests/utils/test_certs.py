"""Tests for certificate generation module."""

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import pytest

from bumper.utils.certs import (
    _build_domain_tree,
    _build_san_list,
    _create_ca_certificate,
    _create_server_certificate,
    _generate_key,
    _generate_wildcards,
    _parse_san_list,
    _write_cert,
    _write_key,
    generate_certificates,
)
from bumper.utils.settings import config as bumper_isc

# Type alias for CA key and certificate fixture
CaKeyAndCert = tuple[ec.EllipticCurvePrivateKey, x509.Certificate]


class TestGenerateEcKey:
    def test_generates_ec_key(self) -> None:
        key = _generate_key()
        assert isinstance(key, ec.EllipticCurvePrivateKey)

    def test_uses_secp256r1_curve(self) -> None:
        key = _generate_key()
        assert isinstance(key.curve, ec.SECP256R1)

    def test_generates_unique_keys(self) -> None:
        key1 = _generate_key()
        key2 = _generate_key()
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


class TestBuildDomainTree:
    def test_builds_tree_from_domains(self) -> None:
        domains = ["sub.example.com", "other.example.com", "test.org"]
        tree = _build_domain_tree(domains)
        assert set(tree.keys()) == {"example.com", "test.org"}
        assert set(tree["example.com"].keys()) == {"sub", "other"}

    def test_handles_deep_subdomains(self) -> None:
        domains = ["a.b.c.example.com"]
        tree = _build_domain_tree(domains)
        assert list(tree.keys()) == ["example.com"]
        assert list(tree["example.com"].keys()) == ["c"]
        assert list(tree["example.com"]["c"].keys()) == ["b"]
        assert list(tree["example.com"]["c"]["b"].keys()) == ["a"]

    def test_handles_root_domain_only(self) -> None:
        domains = ["example.com"]
        tree = _build_domain_tree(domains)
        assert list(tree.keys()) == ["example.com"]
        assert tree["example.com"] == {}

    def test_skips_invalid_domains(self) -> None:
        domains = ["invalid", "example.com"]
        tree = _build_domain_tree(domains)
        assert list(tree.keys()) == ["example.com"]


class TestGenerateWildcards:
    def test_generates_wildcard_for_leaf(self) -> None:
        wildcard_set: set[str] = set()
        node: dict[str, dict[str, dict[str, str]]] = {}
        _generate_wildcards(wildcard_set, node, ["example.com"])
        assert "*.example.com" in wildcard_set

    def test_generates_wildcards_for_nested_structure(self) -> None:
        wildcard_set: set[str] = set()
        node = {"sub": {}}
        _generate_wildcards(wildcard_set, node, ["example.com"])
        assert "*.example.com" in wildcard_set
        assert "*.sub.example.com" in wildcard_set

    def test_generates_wildcards_for_deep_structure(self) -> None:
        wildcard_set: set[str] = set()
        node = {"a": {"b": {"c": {}}}}
        _generate_wildcards(wildcard_set, node, ["example.com"])
        assert "*.example.com" in wildcard_set
        assert "*.a.example.com" in wildcard_set
        assert "*.b.a.example.com" in wildcard_set
        assert "*.c.b.a.example.com" in wildcard_set


class TestBuildSanList:
    def test_includes_localhost_and_ip(self) -> None:
        san_list = _build_san_list()
        assert "IP:127.0.0.1" in san_list
        assert "DNS:localhost" in san_list

    def test_includes_root_domains(self) -> None:
        san_list = _build_san_list()
        assert "DNS:ecovacs.com" in san_list
        assert "DNS:ecouser.net" in san_list
        assert "DNS:aliyun.com" in san_list

    def test_includes_wildcard_domains(self) -> None:
        san_list = _build_san_list()
        assert "DNS:*.ecovacs.com" in san_list
        assert "DNS:*.ecouser.net" in san_list

    def test_san_list_is_sorted(self) -> None:
        san_list = _build_san_list()
        # Skip IP and localhost, check DNS entries are sorted
        dns_entries = [s for s in san_list if s.startswith("DNS:") and s != "DNS:localhost"]
        assert dns_entries == sorted(dns_entries)


class TestParseSanList:
    def test_parses_ip_addresses(self) -> None:
        san_list = _parse_san_list()
        ip_sans = [san for san in san_list if isinstance(san, x509.IPAddress)]
        assert len(ip_sans) >= 1
        assert any(str(san.value) == "127.0.0.1" for san in ip_sans)

    def test_parses_dns_names(self) -> None:
        san_list = _parse_san_list()
        dns_sans = [san for san in san_list if isinstance(san, x509.DNSName)]
        assert len(dns_sans) > 50
        assert any(san.value == "localhost" for san in dns_sans)
        assert any(san.value == "*.ecouser.net" for san in dns_sans)
        assert any(san.value == "*.ecovacs.com" for san in dns_sans)

    def test_san_count_greater_than_raw_domains(self) -> None:
        # Wildcards are generated, so SAN count should be different from raw domain count
        san_list = _parse_san_list()
        # Should have at least IP + localhost + some wildcards
        assert len(san_list) > 2


class TestCreateCaCertificate:
    def test_creates_valid_certificate(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        assert isinstance(cert, x509.Certificate)

    def test_certificate_subject(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert org == "ecovacs"
        assert cn == "ECOVACS CA"

    def test_certificate_is_self_signed(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        assert cert.subject == cert.issuer

    def test_certificate_validity_period(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        validity = cert.not_valid_after_utc - cert.not_valid_before_utc
        expected_days = datetime.timedelta(days=bumper_isc.ca_valid_days)
        assert validity == expected_days

    def test_certificate_has_ca_basic_constraints(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.critical is True
        assert bc.value.ca is True

    def test_certificate_has_key_usage(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.critical is True
        assert ku.value.key_cert_sign is True
        assert ku.value.crl_sign is True
        assert ku.value.digital_signature is False

    def test_certificate_has_subject_key_identifier(self) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        ski = cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        assert ski is not None
        assert ski.critical is False


class TestCreateServerCertificate:
    @pytest.fixture
    def ca_key_and_cert(self) -> CaKeyAndCert:
        ca_key = _generate_key()
        ca_cert = _create_ca_certificate(ca_key)
        return ca_key, ca_cert

    def test_creates_valid_certificate(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        assert isinstance(cert, x509.Certificate)

    def test_certificate_subject(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert org == "ecovacs"
        assert cn == "*.ecouser.net"

    def test_certificate_issuer_matches_ca(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        assert cert.issuer == ca_cert.subject

    def test_certificate_validity_period(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        validity = cert.not_valid_after_utc - cert.not_valid_before_utc
        expected_days = datetime.timedelta(days=bumper_isc.server_valid_days)
        assert validity == expected_days

    def test_certificate_has_key_usage(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.critical is True
        assert ku.value.digital_signature is True
        assert ku.value.key_cert_sign is False

    def test_certificate_has_extended_key_usage(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.SERVER_AUTH in eku.value

    def test_certificate_has_san(self, ca_key_and_cert: CaKeyAndCert) -> None:
        ca_key, ca_cert = ca_key_and_cert
        server_key = _generate_key()
        cert = _create_server_certificate(server_key, ca_key, ca_cert)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        assert san is not None
        # Should have IP + localhost + many wildcard domains
        assert len(san.value) > 50


class TestWriteKey:
    def test_writes_key_to_file(self, tmp_path: Path) -> None:
        key = _generate_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        assert key_path.exists()

    def test_key_file_is_pem_format(self, tmp_path: Path) -> None:
        key = _generate_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        content = key_path.read_text()
        assert content.startswith("-----BEGIN EC " + "PRIVATE KEY-----")
        assert "-----END EC " + "PRIVATE KEY-----" in content

    def test_key_file_has_restricted_permissions(self, tmp_path: Path) -> None:
        key = _generate_key()
        key_path = tmp_path / "test.key"
        _write_key(key, key_path)
        file_stat = key_path.stat()
        assert file_stat.st_mode & 0o777 == 0o600


class TestWriteCert:
    def test_writes_cert_to_file(self, tmp_path: Path) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        cert_path = tmp_path / "test.crt"
        _write_cert(cert, cert_path)
        assert cert_path.exists()

    def test_cert_file_is_pem_format(self, tmp_path: Path) -> None:
        key = _generate_key()
        cert = _create_ca_certificate(key)
        cert_path = tmp_path / "test.crt"
        _write_cert(cert, cert_path)
        content = cert_path.read_text()
        assert content.startswith("-----BEGIN CERTIFICATE-----")
        assert "-----END CERTIFICATE-----" in content


class TestGenerateCertificates:
    @pytest.mark.usefixtures("test_certs")
    def test_generates_all_files(self) -> None:
        result = generate_certificates()

        assert result is True
        assert bumper_isc.ca_cert.exists()
        assert bumper_isc.ca_key.exists()
        assert bumper_isc.server_cert.exists()
        assert bumper_isc.server_key.exists()
        assert bumper_isc.ca_pem.exists()

    @pytest.mark.usefixtures("test_certs")
    def test_skips_if_all_files_exist(self) -> None:
        bumper_isc.certs_dir.mkdir()

        # Create dummy files
        bumper_isc.ca_cert.touch()
        bumper_isc.ca_key.touch()
        bumper_isc.server_cert.touch()
        bumper_isc.server_key.touch()

        result = generate_certificates()

        assert result is False

    @pytest.mark.usefixtures("test_certs")
    def test_generates_if_any_file_missing(self) -> None:
        bumper_isc.certs_dir.mkdir()

        # Create only some files
        bumper_isc.ca_cert.touch()
        bumper_isc.server_cert.touch()

        result = generate_certificates()

        assert result is True

    @pytest.mark.usefixtures("test_certs")
    def test_creates_directory_if_not_exists(self) -> None:
        result = generate_certificates()

        assert result is True
        assert bumper_isc.certs_dir.exists()

    @pytest.mark.usefixtures("test_certs")
    @pytest.mark.parametrize("key_type", ["ec", "rsa", "wrong"])
    def test_ca_pem_contains_all_components(self, key_type: str) -> None:
        bumper_isc.cert_key_type = key_type

        if bumper_isc.cert_key_type == "wrong":
            with pytest.raises(ValueError, match="Wrong Certificate Key Type provided"):
                generate_certificates()
            return

        generate_certificates()

        ca_pem_content = bumper_isc.ca_pem.read_text()
        if bumper_isc.cert_key_type == "ec":
            assert "-----BEGIN EC " + "PRIVATE KEY-----" in ca_pem_content
            assert ca_pem_content.count("-----BEGIN CERTIFICATE-----") == 2
        elif bumper_isc.cert_key_type == "rsa":
            assert "-----BEGIN RSA " + "PRIVATE KEY-----" in ca_pem_content
            assert ca_pem_content.count("-----BEGIN CERTIFICATE-----") == 2

    @pytest.mark.usefixtures("test_certs")
    @pytest.mark.parametrize("key_type", ["ec", "rsa", "wrong"])
    def test_generated_certs_are_valid(self, key_type: str) -> None:
        bumper_isc.cert_key_type = key_type

        if bumper_isc.cert_key_type == "wrong":
            with pytest.raises(ValueError, match="Wrong Certificate Key Type provided"):
                generate_certificates()
            return

        generate_certificates()

        # Load and verify CA cert
        ca_cert_pem = bumper_isc.ca_cert.read_bytes()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)
        cn = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "ECOVACS CA"

        # Load and verify server cert
        server_cert_pem = bumper_isc.server_cert.read_bytes()
        server_cert = x509.load_pem_x509_certificate(server_cert_pem)
        cn = server_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "*.ecouser.net"
        assert server_cert.issuer == ca_cert.subject

        # Load and verify server key
        server_key_pem = bumper_isc.server_key.read_bytes()
        server_key = serialization.load_pem_private_key(server_key_pem, password=None)

        if bumper_isc.cert_key_type == "ec":
            assert isinstance(server_key, ec.EllipticCurvePrivateKey)
        elif bumper_isc.cert_key_type == "rsa":
            assert isinstance(server_key, rsa.RSAPrivateKey)
        else:
            raise AssertionError

    @pytest.mark.usefixtures("test_certs")
    def test_generated_rsa_wrong_size(self) -> None:
        bumper_isc.cert_rsa_key_size = 1024
        bumper_isc.cert_key_type = "rsa"

        with pytest.raises(ValueError, match="RSA key size must be between 2048-4096 bits"):
            generate_certificates()
