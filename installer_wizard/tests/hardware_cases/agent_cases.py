import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from features.hardware import dkms as dkms_mod
from features.hardware import identify
from features.hardware.expert import HardwareAgent
from features.hardware.repos import OsInfo, RepoManager
from .common import dev


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = HardwareAgent()
        self.agent._pkg_manager = "apt"
        self.agent._repos = RepoManager(self.agent._run_cmd, OsInfo("debian", [], "13"), "/nonexistent")
        self.which = mock.patch("features.hardware.expert.shutil.which", return_value="/usr/bin/x")
        self.which.start()

    def tearDown(self):
        self.which.stop()

    def test_unbound_wifi_with_kernel_module_needs_driver(self):
        d = dev(kernel_modules=["foo"])
        status, _, _ = self.agent.diagnose(d)
        self.assertEqual(status, "needs_driver")
        self.assertIn("foo", d.details["reason"])

    def test_bound_device_is_ready(self):
        self.assertEqual(self.agent.diagnose(dev(driver="foo", interface="wlan0", kernel_modules=["foo"]))[0], "ready")

    def test_unbound_without_any_driver_is_unsupported(self):
        self.assertEqual(self.agent.diagnose(dev())[0], "unsupported")

    def test_unbound_with_dkms_recipe_needs_driver(self):
        d = dev(vendor_id="0bda", product_id="8812")
        self.assertEqual(self.agent.diagnose(d)[0], "needs_driver")

    def test_filter_available_parses_policy(self):
        out = "firmware-realtek:\n  Installed: (none)\n  Candidate: 1.0\nnvidia-driver:\n  Installed: (none)\n  Candidate: (none)\n"

        async def run(cmd, timeout=180, env=None):
            return 0, out

        self.agent._run_cmd = run
        ok, skipped = asyncio.run(self.agent.filter_available(["firmware-realtek", "nvidia-driver", "ignoto"]))
        self.assertEqual((ok, skipped), (["firmware-realtek"], ["nvidia-driver", "ignoto"]))

    def _mock_pipeline(self, **overrides):
        steps = []

        async def ok(*a, **k):
            steps.append("x")
            return 0, "ok"

        async def filt(pkgs):
            return list(pkgs), []

        async def none_fw():
            return []

        async def modload(m):
            steps.append(f"modprobe:{m}")
            return True, "caricato"

        async def activate(d):
            return True

        class Repo:
            changed, ok, enabled, already, notes, backups = True, True, ["non-free"], [], [], ["/b"]

        async def ensure(repos, pm):
            steps.append(f"repos:{','.join(repos)}")
            return Repo()

        patches = [
            mock.patch.object(self.agent, "update_packages", ok),
            mock.patch.object(self.agent, "install_packages", ok),
            mock.patch.object(self.agent, "filter_available", filt),
            mock.patch.object(self.agent, "_scan_dmesg_missing_firmware", none_fw),
            mock.patch.object(self.agent, "load_module_safely", modload),
            mock.patch.object(self.agent, "activate_device", activate),
            mock.patch.object(self.agent.repos, "ensure", ensure),
            mock.patch("features.hardware.pipeline.reprobe", return_value=False),
            mock.patch.object(self.agent, "_rebind", lambda d: (setattr(d, "interface", d.interface or "wlan0") or identify.Identity(bus=d.bus, sys_id=d.sys_id, bound_driver=d.driver or "test_driver", interface=d.interface or "wlan0"))),
            mock.patch.object(self.agent.repos, "restore", return_value=["/b"]),
        ]
        for k, v in overrides.items():
            patches.append(mock.patch.object(self.agent, k, v))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return steps

    def test_pipeline_dkms_from_source(self):
        steps = self._mock_pipeline()
        calls = []

        async def toolchain(pm, fam):
            calls.append("toolchain")
            return True, "ok"

        async def from_git(spec):
            calls.append(f"git:{spec['module']}")
            return dkms_mod.DkmsResult(ok=True, module=spec["module"], message="installato")

        self.agent._dkms = mock.Mock(ensure_toolchain=toolchain, install_from_git=from_git)
        d = dev(vendor_id="0bda", product_id="8812", id="usb:0bda:8812:1-1")
        self.assertTrue(asyncio.run(self.agent.provision(d)))
        self.assertEqual(d.status, "ready")
        self.assertEqual(calls, ["toolchain", "git:88XXau"])
        self.assertIn("modprobe:88XXau", steps)
        self.assertTrue(any(s["tier"] == "dkms" and s["ok"] for s in d.steps))
        self.assertEqual(d.capabilities, ["network.wifi"])

    def test_pipeline_dkms_failure_reports_error(self):
        self._mock_pipeline()

        async def toolchain(pm, fam):
            return True, "ok"

        async def from_git(spec):
            return dkms_mod.DkmsResult(ok=False, message="build error")

        self.agent._dkms = mock.Mock(ensure_toolchain=toolchain, install_from_git=from_git)
        d = dev(vendor_id="0bda", product_id="8812", id="usb:0bda:8812:1-1")
        self.assertFalse(asyncio.run(self.agent.provision(d)))
        self.assertEqual(d.status, "error")
        self.assertEqual(d.capabilities, [])

    def _gpu_dev(self):
        return dev(category="gpu", bus="pci", vendor_id="10de", product_id="1c82", driver="nouveau", id="pci:10de:1c82:0000:01:00.0", sys_id="0000:01:00.0")

    def test_gpu_waits_for_approval_then_requires_reboot(self):
        async def verify_fails(cmd, timeout=180, env=None):
            return 1, "nvidia-smi: driver non caricato"

        self._mock_pipeline(_run_cmd=verify_fails)
        d = self._gpu_dev()
        with mock.patch("features.hardware.accelerators.has_graphical_session", return_value=True):
            self.assertFalse(asyncio.run(self.agent.provision(d)))
            self.assertEqual(d.status, "awaiting_approval")
            self.assertEqual(d.capabilities, [])
            self.assertTrue(asyncio.run(self.agent.provision(d, approve=True)))
        self.assertEqual(d.status, "reboot_required", d.steps)
        self.assertTrue(any(s["tier"] == "repository" for s in d.steps))

    def test_gpu_ready_when_driver_verifies(self):
        async def verify_ok(cmd, timeout=180, env=None):
            return 0, "00000000:01:00.0"

        self._mock_pipeline(_run_cmd=verify_ok)
        d = self._gpu_dev()
        with mock.patch.object(self.agent, "_rebind", side_effect=lambda d: (setattr(d, "driver", "nvidia") or identify.Identity(bus="pci", sys_id=d.sys_id, bound_driver="nvidia"))), mock.patch("features.hardware.accelerators.has_graphical_session", return_value=False):
            self.assertTrue(asyncio.run(self.agent.provision(d)))
        self.assertEqual(d.status, "ready")
        self.assertEqual(d.capabilities, ["graphics.render", "compute.accelerator"])

    def test_unsupported_is_not_provisioned(self):
        self._mock_pipeline()
        d = dev()
        self.assertFalse(asyncio.run(self.agent.provision(d)))
        self.assertEqual(d.status, "unsupported")

    def test_load_module_rollback_blacklists_crashing_module(self):
        calls = []

        async def run(cmd, timeout=180, env=None):
            calls.append(cmd[0])
            if cmd[0] == "dmesg":
                return 0, "bad_mod: BUG: unable to handle kernel NULL pointer\n" if calls.count("dmesg") > 1 else ""
            return 0, ""

        self.agent._run_cmd = run
        with tempfile.TemporaryDirectory() as d, mock.patch("features.hardware.expert.BLACKLIST_DIR", Path(d)):
            ok, note = asyncio.run(self.agent.load_module_safely("bad_mod"))
            self.assertFalse(ok)
            self.assertGreaterEqual(calls.count("modprobe"), 3)
            self.assertIn("blacklist bad_mod", (Path(d) / "nuxiva-blacklist-bad_mod.conf").read_text())

    def test_load_module_rejects_injection(self):
        ok, note = asyncio.run(self.agent.load_module_safely("x; rm -rf /"))
        self.assertFalse(ok)
