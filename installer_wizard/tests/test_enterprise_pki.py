import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12

from enterprise_pki import (
    calculate_fingerprint,
    generate_client_bundle,
    generate_enterprise_ca,
    generate_server_certificate,
    get_pki_status,
)


class TestEnterprisePki(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.test_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_generate_enterprise_ca(self):
        ca_pem, ca_key = generate_enterprise_ca(self.test_dir, organization="Acme Corp")
        self.assertTrue(ca_pem.exists())
        self.assertTrue(ca_key.exists())

        ca_cert = x509.load_pem_x509_certificate(ca_pem.read_bytes())
        self.assertEqual(ca_cert.issuer, ca_cert.subject)
        bc = ca_cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        self.assertTrue(bc.ca)

        fp = calculate_fingerprint(ca_pem.read_bytes())
        self.assertRegex(fp, r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$")

    def test_generate_server_certificate_with_sans(self):
        ca_pem, ca_key = generate_enterprise_ca(self.test_dir)
        fake_ifaces = [
            {"name": "tailscale0", "addresses": ["100.115.92.10"], "is_tailscale": True, "is_vpn": False},
            {"name": "wg0", "addresses": ["10.8.0.1"], "is_tailscale": False, "is_vpn": True},
            {"name": "eth0", "addresses": ["192.168.1.88"], "is_tailscale": False, "is_vpn": False},
        ]

        with patch("enterprise_pki.discover_interfaces", return_value=fake_ifaces), \
             patch("enterprise_pki.discover_tailscale_fqdn", return_value="my-node.tailnet.ts.net"):
            srv_pem, srv_key = generate_server_certificate(
                self.test_dir,
                ca_pem,
                ca_key,
                custom_dns=["secure.example.com"],
                custom_ips=["10.99.0.1"],
                include_tailscale=True,
                include_vpn=True,
            )

        self.assertTrue(srv_pem.exists())
        self.assertTrue(srv_key.exists())

        srv_cert = x509.load_pem_x509_certificate(srv_pem.read_bytes())
        san_ext = srv_cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns_names = san_ext.get_values_for_type(x509.DNSName)
        ip_names = [str(ip) for ip in san_ext.get_values_for_type(x509.IPAddress)]

        self.assertIn("my-node.tailnet.ts.net", dns_names)
        self.assertIn("secure.example.com", dns_names)
        self.assertIn("100.115.92.10", ip_names)
        self.assertIn("10.8.0.1", ip_names)
        self.assertIn("192.168.1.88", ip_names)
        self.assertIn("10.99.0.1", ip_names)

    def test_generate_client_bundle_pkcs12(self):
        ca_pem, ca_key = generate_enterprise_ca(self.test_dir)
        p12_bytes = generate_client_bundle(self.test_dir, client_identity="operator-tablet", password="pass")
        self.assertGreater(len(p12_bytes), 500)

        key, cert, chain = pkcs12.load_key_and_certificates(p12_bytes, b"pass")
        self.assertIsNotNone(key)
        self.assertIsNotNone(cert)
        self.assertEqual(len(chain), 1)

    def test_get_pki_status(self):
        status_empty = get_pki_status(self.test_dir)
        self.assertFalse(status_empty.has_ca)
        self.assertFalse(status_empty.has_server_cert)

        ca_pem, ca_key = generate_enterprise_ca(self.test_dir)
        generate_server_certificate(self.test_dir, ca_pem, ca_key)

        status = get_pki_status(self.test_dir)
        self.assertTrue(status.has_ca)
        self.assertTrue(status.has_server_cert)
        self.assertIn("CN=", status.ca_subject)
        self.assertTrue(len(status.sans) > 0)
