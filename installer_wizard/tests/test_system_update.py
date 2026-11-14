import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center import system_plan, system_runner

SIM = (
    "Reading package lists...\nThe following packages have been kept back:\n  linux-generic foo\n"
    "The following packages will be upgraded:\n  libc6 curl\n"
    "Inst libc6 [2.36-9] (2.36-9+deb12u7 Debian-Security:12/stable-security [amd64])\n"
    "Inst curl [7.88] (7.88.1-10 Debian:12.5/stable [amd64])\n"
    "Inst libnew (1.0 Debian:12/stable [amd64])\nRemv oldpkg [1.0]\n"
    "Conf libc6 (2.36-9+deb12u7 Debian-Security:12/stable-security [amd64])\n"
)
SAFE = "Inst curl [7.88] (7.88.1-10 Debian:12.5/stable [amd64])\n"


class PlanTests(unittest.TestCase):
    def test_parse_and_plan(self):
        sim = system_plan._py_parse(SIM)
        self.assertEqual(len(sim["upgrades"]), 2)
        self.assertEqual(sim["installs"], ["libnew"])
        self.assertEqual(sim["removals"], ["oldpkg"])
        self.assertEqual(sim["kept_back"], ["linux-generic", "foo"])
        plan = system_plan._py_plan(SIM, True, "abc")
        self.assertEqual([s["id"] for s in plan["steps"]], ["debian", "nuxiva"])
        self.assertEqual(plan["risk"], "high")
        self.assertTrue(plan["needs_confirmation"] and plan["reboot_likely"])
        self.assertEqual(system_plan._py_plan(SAFE, False, "")["risk"], "low")

    def test_hostile_names_rejected(self):
        sim = system_plan._py_parse("Inst ;rm [1] (2 x)\nInst -y [1] (2 x)\nRemv $(x) [1]\n")
        self.assertEqual(sim, {"upgrades": [], "installs": [], "removals": [], "kept_back": []})

    def test_plan_id_is_stable_and_target_sensitive(self):
        a = system_plan._py_plan(SIM, True, "abc")["id"]
        self.assertEqual(a, system_plan._py_plan(SIM, True, "abc")["id"])
        self.assertNotEqual(a, system_plan._py_plan(SIM, True, "abd")["id"])
        self.assertEqual(len(a), 16)

    def test_auto_config_security_only(self):
        files = {f["name"]: f["content"] for f in system_plan._py_auto_config(True)}
        self.assertIn('Unattended-Upgrade "1"', files["20nuxiva-auto-upgrades"])
        self.assertIn('Automatic-Reboot "false"', files["52nuxiva-unattended-upgrades"])
        off = {f["name"]: f["content"] for f in system_plan._py_auto_config(False)}
        self.assertIn('Unattended-Upgrade "0"', off["20nuxiva-auto-upgrades"])

    @unittest.skipUnless(system_plan.RUST, "nuxiva_native non installato")
    def test_rust_python_parity(self):
        for raw, nux in ((SIM, True), (SAFE, False), ("", False)):
            self.assertEqual(system_plan.parse(raw), system_plan._py_parse(raw))
            self.assertEqual(system_plan.plan(raw, nux, "abc"), system_plan._py_plan(raw, nux, "abc"))
        for enabled in (True, False):
            self.assertEqual(system_plan.auto_config(enabled), system_plan._py_auto_config(enabled))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for patch in (
            mock.patch.object(system_runner, "RUN_FILE", root / "run.json"),
            mock.patch.object(system_runner, "PENDING_FILE", root / "pending.json"),
            mock.patch.object(system_runner, "isolate", lambda cmd: cmd),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.events = []
        self.calls = []

    def sh_factory(self, fail_upgrade=False):
        async def sh(*cmd, timeout=60):
            self.calls.append(cmd)
            if "dist-upgrade" in cmd and "-s" not in cmd:
                return (100, "E: boom") if fail_upgrade else (0, "ok")
            return 0, "curl=7.88"
        return sh

    def run_plan(self, plan, fail_upgrade=False):
        order = []

        async def nuxiva():
            order.append("nuxiva")
            return True

        data = asyncio.run(system_runner.execute(self.sh_factory(fail_upgrade), plan, nuxiva, lambda l, m: self.events.append((l, m))))
        return data, order

    def test_debian_runs_before_nuxiva(self):
        plan = system_plan._py_plan(SAFE, True, "abc")
        data, order = self.run_plan(plan)
        self.assertEqual(data["status"], "done")
        self.assertEqual(order, ["nuxiva"])
        ids = [s["id"] for s in data["steps"]]
        self.assertLess(ids.index("debian"), ids.index("nuxiva"))
        self.assertEqual(system_runner.last_run()["plan"], plan["id"])

    def test_debian_failure_skips_nuxiva_and_recovers(self):
        plan = system_plan._py_plan(SAFE, True, "abc")
        data, order = self.run_plan(plan, fail_upgrade=True)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(order, [])
        statuses = {s["id"]: s["status"] for s in data["steps"]}
        self.assertEqual(statuses["nuxiva"], "skipped")
        self.assertEqual(statuses["debian"], "failed")
        self.assertTrue(any("--configure" in c for c in self.calls))
        self.assertTrue(any(level == "ERROR" for level, _ in self.events))

    def test_confirmation_is_bound_to_plan(self):
        system_runner.request_confirmation("aaaa")
        self.assertTrue(system_runner.confirmation_valid("aaaa"))
        self.assertFalse(system_runner.confirmation_valid("bbbb"))
        system_runner.clear_confirmation()
        self.assertFalse(system_runner.confirmation_valid("aaaa"))

    def test_apt_command_uses_noninteractive_and_lock_timeout(self):
        cmd = system_runner.apt_command("-y", "dist-upgrade")
        self.assertIn("DEBIAN_FRONTEND=noninteractive", cmd)
        self.assertIn("DPkg::Lock::Timeout=300", cmd)

    def test_auto_security_skipped_without_root_context(self):
        with mock.patch.object(system_runner, "DEMO", True):
            result = asyncio.run(system_runner.sync_auto_security(self.sh_factory(), True, lambda l, m: None))
        self.assertEqual(result, "skipped")


if __name__ == "__main__":
    unittest.main()
