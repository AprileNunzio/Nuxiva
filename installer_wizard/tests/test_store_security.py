import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agenti.store.integrity import (
    validate_package_security_contract,
    verify_sha256_checksum,
)
from agenti.store.sandbox_bridge import (
    build_sandbox_profile_for_package,
)


class TestStoreSecurityIntegrity(unittest.TestCase):
    def test_verify_sha256_checksum(self):
        data = b"nuxiva-zero-trust-package"
        valid_hash = "5d401e41a540a342a4506d84ccd5786341a2ebba1ab108beb08eeeb800b344ef"
        self.assertTrue(verify_sha256_checksum(data, valid_hash))
        self.assertTrue(verify_sha256_checksum(data, f"sha256:{valid_hash}"))
        self.assertFalse(verify_sha256_checksum(data, "0" * 64))
        self.assertFalse(verify_sha256_checksum(data, "invalid_len"))

    def test_validate_package_security_contract(self):
        valid_pkg = {
            "id": "my_valid_app",
            "title": "My Valid App",
            "category": "productivity",
            "size_gb": 1.2,
            "capabilities": ["local_storage", "webgl2"],
            "allowed_hosts": ["api.example.com"],
        }
        ok, reason = validate_package_security_contract(valid_pkg)
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_validate_package_rejects_invalid_id(self):
        bad_pkg = {
            "id": "../malicious/path",
            "title": "Bad App",
        }
        ok, reason = validate_package_security_contract(bad_pkg)
        self.assertFalse(ok)
        self.assertEqual(reason, "package_id_invalid_format")

    def test_validate_package_rejects_excessive_size(self):
        bad_pkg = {
            "id": "giant_pack",
            "title": "Giant",
            "size_gb": 999999.0,
        }
        ok, reason = validate_package_security_contract(bad_pkg)
        self.assertFalse(ok)
        self.assertEqual(reason, "package_size_out_of_bounds")

    def test_build_sandbox_profile_airgap(self):
        pkg = {
            "id": "offline_game",
            "capabilities": ["local_storage"],
            "size_gb": 0.5,
        }
        profile = build_sandbox_profile_for_package(pkg)
        self.assertEqual(profile.network_policy, "none")
        self.assertEqual(profile.allowed_hosts, [])
        self.assertLessEqual(profile.memory_mb, 512)

    def test_build_sandbox_profile_with_egress(self):
        pkg = {
            "id": "cloud_sync_plugin",
            "capabilities": ["network_fetch"],
            "allowed_hosts": ["sync.nuxiva.org"],
            "size_gb": 2.5,
        }
        profile = build_sandbox_profile_for_package(pkg)
        self.assertEqual(profile.network_policy, "allowlist")
        self.assertIn("sync.nuxiva.org", profile.allowed_hosts)
        self.assertEqual(profile.cpus, 1.0)
        self.assertEqual(profile.pids, 128)


if __name__ == "__main__":
    unittest.main()
