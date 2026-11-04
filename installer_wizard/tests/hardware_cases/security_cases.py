import asyncio
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from features.hardware import capabilities, dkms, identify
from features.hardware.apt_sources import deb822, source_lines
from features.hardware.catalog_validation import validate_catalog
from features.hardware.execution import run_command
from features.hardware.gpu_verification import verified_capabilities
from features.hardware.managed import ManagedDevices
from features.hardware.modules import load_module
from features.hardware.repos import OsInfo, RepoManager
from . import dkms_cases
from .common import dev


class RepositorySecurityTest(unittest.TestCase):
    def test_spoofed_hosts_and_inline_comments(self):
        info = OsInfo("debian", [], "13")
        for uri in ("https://debian.org.evil.test/repo", "https://evil.test/debian.org", "https://debian.org@evil.test/repo"):
            original = f"deb {uri} stable main\n"
            self.assertEqual(source_lines(original, ["non-free"], info), (original, []))
        text, added = source_lines("deb https://deb.debian.org/debian stable main # retain\n", ["non-free"], info)
        self.assertIn("main non-free # retain", text)
        self.assertEqual(added, ["non-free"])

    def test_disabled_or_mixed_deb822_sources_are_preserved(self):
        for uri, enabled in (("https://deb.debian.org/debian https://evil.test", "yes"),
                             ("https://deb.debian.org/debian", "no")):
            original = f"Types: deb\nURIs: {uri}\nComponents: main\nEnabled: {enabled}\n"
            self.assertEqual(deb822(original, ["non-free"], OsInfo("debian")), (original, []))

    def test_multiline_deb822_uses_every_uri_and_preserves_signing_key(self):
        original = "Types: deb\nURIs: https://deb.debian.org/debian\n https://security.debian.org/debian-security\nComponents: main\n contrib\nSigned-By: /key.gpg\n"
        text, added = deb822(original, ["non-free"], OsInfo("debian"))
        self.assertIn("Components: main contrib non-free", text)
        self.assertIn("Signed-By: /key.gpg", text)
        self.assertEqual(added, ["non-free"])

    def test_missing_official_sources_are_not_reported_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            manager = RepoManager(mock.AsyncMock(), OsInfo("debian", [], "13"), root)
            result = asyncio.run(manager.ensure(["non-free"], "apt"))
            self.assertFalse(result.ok)
            self.assertEqual(result.already, [])

    def test_restore_refuses_foreign_path_and_concurrent_changes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "sources.list")
            path.write_text("deb https://deb.debian.org/debian stable main\n")
            manager = RepoManager(mock.AsyncMock(), OsInfo("debian", [], "13"), root)
            result = asyncio.run(manager.ensure(["non-free"], "apt"))
            path.write_text("administrator changes\n")
            with self.assertLogs("nuxiva.hardware.repos", level="ERROR"):
                self.assertEqual(manager.restore(result.backups), [])
            self.assertEqual(path.read_text(), "administrator changes\n")
            with self.assertRaises(ValueError):
                manager.restore([str(Path(root).parent / "foreign.nuxiva-bak-123")])

    def test_rhel_family_is_not_misidentified_as_fedora(self):
        self.assertEqual(OsInfo("rocky", ["rhel", "centos", "fedora"], "9").family, "rhel")


class DriverSourceSecurityTest(unittest.TestCase):
    spec = {"git": "https://github.com/aircrack-ng/rtl8812au.git", "module": "rtlfake", "revision": "a" * 40}

    def broker(self, root, fail_step=""):
        return dkms_cases.DkmsTest._broker(self, root, fail_step)

    def test_unpinned_or_untrusted_sources_never_execute(self):
        for spec in ({**self.spec, "revision": "main"}, {**self.spec, "git": "https://github.com/attacker/driver.git"},
                     {**self.spec, "module": "--all"}):
            with tempfile.TemporaryDirectory() as root:
                broker, calls = self.broker(Path(root))
                self.assertFalse(asyncio.run(broker.install_from_git(spec)).ok)
                self.assertEqual(calls, [])

    def test_existing_sources_survive_and_are_not_removed_from_dkms(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root, "rtlfake-1.0")
            target.mkdir()
            marker = target / "owner.txt"
            marker.write_text("administrator")
            broker, calls = self.broker(Path(root))
            result = asyncio.run(broker.install_from_git(self.spec))
            self.assertFalse(result.ok)
            self.assertEqual(marker.read_text(), "administrator")
            self.assertFalse(any(c[:2] == ["dkms", "remove"] for c in calls))

    def test_failed_add_does_not_remove_foreign_registration(self):
        with tempfile.TemporaryDirectory() as root:
            broker, calls = self.broker(Path(root), "add")
            self.assertFalse(asyncio.run(broker.install_from_git(self.spec)).ok)
            self.assertFalse(any(c[:2] == ["dkms", "remove"] for c in calls))
            self.assertFalse(Path(root, "rtlfake-1.0").exists())

    def test_pinned_install_is_idempotent_without_force(self):
        with tempfile.TemporaryDirectory() as root:
            broker, calls = self.broker(Path(root))
            self.assertTrue(asyncio.run(broker.install_from_git(self.spec)).ok)
            calls.clear()
            self.assertTrue(asyncio.run(broker.install_from_git(self.spec)).ok)
            self.assertFalse(any(c[:2] == ["dkms", "add"] for c in calls))
            self.assertFalse(any("--force" in c for c in calls))

    def test_secure_boot_is_never_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            run = mock.AsyncMock(return_value=(0, "SecureBoot enabled"))
            broker = dkms.DkmsBroker(run, mock.AsyncMock(), Path(root))
            with mock.patch.object(dkms, "kernel_release", return_value="test-kernel"), \
                 mock.patch.object(Path, "exists", return_value=True):
                result = asyncio.run(broker.install_from_git(self.spec))
            self.assertFalse(result.ok)
            self.assertIn("Secure Boot", result.message)
            run.assert_awaited_once_with(["mokutil", "--sb-state"], timeout=20)

    def test_catalog_rejects_command_options_and_unpinned_sources(self):
        for recipe in ({"packages": {"apt": ["--allow-unauthenticated"]}}, {"modules": ["--remove"]},
                       {"firmware": ["../../etc/passwd"]}, {"dkms": {"git": self.spec["git"]}}):
            with self.assertRaises(ValueError):
                validate_catalog({"recipes": [{"id": "sample", **recipe}]})


class VerificationSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def test_historical_kernel_error_does_not_unload_a_module(self):
        run = mock.AsyncMock(side_effect=[(0, ""), (0, "old BUG: trace\n"), (0, ""), (0, "old BUG: trace\n")])
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue((await load_module("test_mod", run, Path(root)))[0])
        self.assertFalse(any(call.args[0][:2] == ["modprobe", "-r"] for call in run.call_args_list))

    async def test_gpu_compute_requires_matching_pci_address(self):
        device = dev(category="gpu", vendor_id="10de", sys_id="0000:01:00.0", driver="nvidia")
        with mock.patch("features.hardware.gpu_verification.shutil.which", return_value="nvidia-smi"):
            self.assertEqual(await verified_capabilities(device, mock.AsyncMock(return_value=(0, "00000000:02:00.0"))), [])
            self.assertEqual(await verified_capabilities(device, mock.AsyncMock(return_value=(0, "00000000:01:00.0"))), ["compute.accelerator"])

    async def test_command_timeout_reaps_the_process(self):
        start = time.monotonic()
        with self.assertLogs("nuxiva.hardware.execution", level="ERROR"):
            code, _ = await run_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
        self.assertEqual(code, 124)
        self.assertLess(time.monotonic() - start, 3)

    def test_non_ready_device_cannot_publish_stale_capabilities(self):
        self.assertEqual(capabilities.aggregate([dev(status="error", capabilities=["network.wifi"])]), {})

    def test_registry_survives_restart_and_scopes_updates(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "managed.json")
            device = dev(required_packages=["firmware-realtek"])
            registry = ManagedDevices(path)
            with mock.patch("features.hardware.managed.time.time", return_value=100):
                registry.record(device)
            restarted = ManagedDevices(path)
            with mock.patch("features.hardware.managed.time.time", return_value=100000):
                self.assertTrue(restarted.due(device.id))
                self.assertFalse(restarted.due("unmanaged"))
            self.assertEqual(json.loads(path.read_text())["devices"][device.id]["packages"], ["firmware-realtek"])

    def test_alias_index_refreshes_after_dkms_changes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "modules.alias")
            path.write_text("alias acpi*:TEST:* first\n")
            index = identify.ModulesAlias(path)
            self.assertEqual(index.modules_for("acpi:TEST:"), ["first"])
            path.write_text("alias acpi*:TEST:* replacement\n")
            self.assertEqual(index.modules_for("acpi:TEST:"), ["replacement"])
