import asyncio
import tempfile
import unittest
from pathlib import Path

from server.features.password_vault.models import SecretCategory, VaultEntryCreate
from server.features.password_vault.vault_service import UserPasswordVaultService, password_vault_service
from server.features.device_provisioner.models import DebianProvisionRequest, Esp32ProvisionRequest
from server.features.device_provisioner.esp32_provisioner import _classify_usb_ids, esp32_provisioner
from server.features.device_provisioner.debian_provisioner import debian_provisioner
from server.cmd.route_scanner import route_scanner


class TestPasswordVaultAndDeviceProvisioner(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault = UserPasswordVaultService(storage_dir=Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_vault_encryption_lifecycle_and_zero_plaintext_on_disk(self):
        uid = "nunzio_test"
        status = self.vault.get_status(uid)
        self.assertFalse(status.initialized)
        self.assertFalse(status.unlocked)

        # Inizializza e sblocca
        unlocked = self.vault.unlock_or_initialize(uid, "MasterPass#2026!")
        self.assertTrue(unlocked.initialized)
        self.assertTrue(unlocked.unlocked)

        # Aggiungi segreto SSH
        secret_value = "SuperSecretSshPass!99"
        meta = self.vault.add_entry(
            uid,
            VaultEntryCreate(
                label="Debian Casa",
                category=SecretCategory.SSH,
                host_or_url="192.168.1.50",
                port=22,
                username="admin",
                secret=secret_value,
            ),
        )
        self.assertTrue(meta.has_secret)
        self.assertNotIn(secret_value, meta.masked_preview)

        # Verifica che su disco il segreto NON compaia mai in chiaro
        disk_text = (Path(self._tmpdir.name) / f"{uid}.vault.json").read_text(encoding="utf-8")
        self.assertNotIn(secret_value, disk_text)
        self.assertNotIn("MasterPass#2026!", disk_text)

        # Reveal mentre sbloccato
        revealed = self.vault.reveal_entry(uid, meta.entry_id)
        self.assertEqual(revealed.secret, secret_value)

        # Blocca: reveal deve fallire
        self.vault.lock(uid)
        with self.assertRaises(PermissionError):
            self.vault.reveal_entry(uid, meta.entry_id)

        # Master password errata deve fallire
        with self.assertRaises(PermissionError):
            self.vault.unlock_or_initialize(uid, "WrongPassword")

        # Sblocca nuovamente ed elimina
        self.vault.unlock_or_initialize(uid, "MasterPass#2026!")
        self.assertTrue(self.vault.delete_entry(uid, meta.entry_id))
        self.assertEqual(self.vault.list_entries(uid), [])

    def test_strong_password_generator(self):
        pwd = self.vault.generate_strong_password(length=24, include_symbols=True)
        self.assertEqual(len(pwd), 24)
        self.assertTrue(any(c.islower() for c in pwd))
        self.assertTrue(any(c.isupper() for c in pwd))
        self.assertTrue(any(c.isdigit() for c in pwd))
        self.assertTrue(any(c in "!@#$%^&*-_=+" for c in pwd))

    def test_esp32_usb_signature_classification(self):
        hint_cp, likely_cp = _classify_usb_ids("10C4", "EA60")
        self.assertTrue(likely_cp)
        self.assertIn("CP210x", hint_cp)

        hint_s3, likely_s3 = _classify_usb_ids("303A", "1001")
        self.assertTrue(likely_s3)
        self.assertIn("Espressif", hint_s3)

        _, likely_other = _classify_usb_ids("0000", "0000", "Mouse")
        self.assertFalse(likely_other)

    def test_esp32_and_debian_provisioners_with_user_vault_dry_run(self):
        # Usa un'istanza temporanea collegata al singleton solo durante il test
        orig_dir = password_vault_service._storage_dir
        orig_sessions = dict(password_vault_service._unlocked_sessions)
        try:
            password_vault_service._storage_dir = Path(self._tmpdir.name)
            password_vault_service._unlocked_sessions.clear()

            uid = "user_prov_test"
            password_vault_service.unlock_or_initialize(uid, "VaultKey#1234")
            wifi_entry = password_vault_service.add_entry(
                uid,
                VaultEntryCreate(
                    label="Wi-Fi Casa",
                    category=SecretCategory.WIFI,
                    username="CasaNuxiva5G",
                    secret="WifiSecret2026!",
                ),
            )
            ssh_entry = password_vault_service.add_entry(
                uid,
                VaultEntryCreate(
                    label="Debian Lab",
                    category=SecretCategory.SSH,
                    host_or_url="192.168.1.90",
                    port=22,
                    username="debian",
                    secret="DebianPass2026!",
                ),
            )

            esp_res = asyncio.run(
                esp32_provisioner.provision(
                    Esp32ProvisionRequest(
                        user_id=uid,
                        wifi_vault_entry_id=wifi_entry.entry_id,
                        nuxiva_server_url="http://192.168.1.10:80",
                        dry_run=True,
                    )
                )
            )
            self.assertTrue(esp_res.success)
            self.assertTrue(any(s.step == "vault_credentials" and s.status == "ok" for s in esp_res.steps))

            deb_res = asyncio.run(
                debian_provisioner.provision(
                    DebianProvisionRequest(
                        user_id=uid,
                        host="192.168.1.90",
                        username="debian",
                        ssh_vault_entry_id=ssh_entry.entry_id,
                        install_mode="satellite",
                        dry_run=True,
                    )
                )
            )
            self.assertTrue(deb_res.success)
            self.assertTrue(any(s.step == "vault_credentials" and s.status == "ok" for s in deb_res.steps))

            # Injection guard sul target Debian
            bad_res = asyncio.run(
                debian_provisioner.provision(
                    DebianProvisionRequest(
                        user_id=uid,
                        host="192.168.1.90; rm -rf /",
                        username="root",
                        dry_run=True,
                    )
                )
            )
            self.assertFalse(bad_res.success)
        finally:
            password_vault_service._storage_dir = orig_dir
            password_vault_service._unlocked_sessions = orig_sessions

    def test_routers_auto_discovered_by_route_scanner(self):
        routers = route_scanner.scan_routers()
        prefixes = {r.prefix for r in routers}
        self.assertIn("/vault", prefixes)
        self.assertIn("/provisioner", prefixes)


if __name__ == "__main__":
    unittest.main()
