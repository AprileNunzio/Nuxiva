import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "installer_wizard" / "reboot_gate.sh"
BOOTSTRAP = ROOT / "installer_wizard" / "bootstrap.sh"
INSTALL = ROOT / "install.sh"


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "bash and jq required")
class RebootGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nuxiva-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.calls = self.tmp / "calls.log"
        self.counter = self.tmp / "busy"
        self.counter.write_text("0", encoding="utf-8")
        self.stub("systemctl", f'printf "%s\\n" "$*" >> "{self.calls}"\nexit "${{SYSTEMCTL_RC:-0}}"')
        self.stub("systemd-run", f'printf "systemd-run %s\\n" "$*" >> "{self.calls}"')
        self.stub("sleep", "exit 0")
        self.stub("busctl", 'if [ -n "${INHIBITORS:-}" ]; then printf "%s" "$INHIBITORS"; else exit 1; fi')
        self.stub(
            "pgrep",
            f'[ "$2" = "apt-get" ] || exit 1\n'
            f'n=$(cat "{self.counter}")\n'
            f'[ "$n" -gt 0 ] || exit 1\n'
            f'echo $((n - 1)) > "{self.counter}"\n'
            f'exit 0',
        )

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def run_gate(self, script, busy=0, inhibitors=None, rc=0):
        self.counter.write_text(str(busy), encoding="utf-8")
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "REBOOT_GATE_LOCKS": str(self.tmp / "missing-lock"),
            "SYSTEMCTL_RC": str(rc),
            "HOME": str(self.tmp),
        }
        if inhibitors is not None:
            env["INHIBITORS"] = json.dumps(inhibitors)
        return subprocess.run(
            ["bash", "-c", f'set -Eeuo pipefail; source "{GATE}"; {script}'],
            capture_output=True, text=True, env=env, timeout=30,
        )

    def calls_made(self):
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def test_waits_for_apt_before_rebooting(self):
        result = self.run_gate(
            'seen=0; note() { seen=$((seen + 1)); }; reboot_gate_run 600 note; echo "seen=$seen"', busy=3
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("seen=3", result.stdout)
        self.assertEqual(self.calls_made(), ["reboot -i"])

    def test_never_reboots_while_apt_is_still_running(self):
        result = self.run_gate("reboot_gate_wait 0", busy=50)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(), "apt-get")
        self.assertEqual(self.calls_made(), [])

    def test_run_reports_busy_without_false_success(self):
        result = self.run_gate("reboot_gate_run 0", busy=50)
        self.assertEqual(result.returncode, 75)
        self.assertEqual(self.calls_made(), [])

    def test_honours_logind_block_inhibitor_of_apt(self):
        inhibitors = {"type": "a(ssssuu)", "data": [[
            ["sleep", "GNOME", "idle", "delay", 1000, 10],
            ["shutdown:sleep", "APT", "APT is installing or removing packages", "block", 0, 9518],
        ]]}
        result = self.run_gate("reboot_gate_blocker", inhibitors=inhibitors)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "APT (PID 9518)")

    def test_ignores_delay_inhibitors_and_user_sessions(self):
        inhibitors = {"type": "a(ssssuu)", "data": [[["shutdown", "NetworkManager", "sync", "delay", 0, 42]]]}
        result = self.run_gate("reboot_gate_run 5", inhibitors=inhibitors)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls_made(), ["reboot -i"])

    def test_retries_and_fails_honestly_when_systemctl_refuses(self):
        result = self.run_gate("reboot_gate_run 5", rc=1)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.calls_made(), ["reboot -i"] * 3)

    def test_rejects_invalid_limit(self):
        self.assertEqual(self.run_gate("reboot_gate_run abc").returncode, 64)

    def test_defer_hands_off_to_transient_unit(self):
        result = self.run_gate("reboot_gate_defer 21600")
        self.assertEqual(result.returncode, 0, result.stderr)
        handoff = [c for c in self.calls_made() if c.startswith("systemd-run")]
        self.assertEqual(len(handoff), 1)
        self.assertIn("--unit=nuxiva-first-reboot", handoff[0])
        self.assertTrue(handoff[0].endswith(f"{GATE} run 21600"))


class BootstrapRebootTest(unittest.TestCase):
    def test_bootstrap_no_longer_reboots_blindly(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("reboot || sudo reboot", text)
        self.assertNotIn("Rebooting system in 5 seconds", text)
        self.assertIn("restart_when_idle || exit 1", text)
        for key in ("reboot_wait", "reboot_now", "reboot_deferred", "reboot_manual"):
            self.assertEqual(text.count(f"[{key}]="), 2, key)

    @unittest.skipUnless(shutil.which("bash"), "bash required")
    def test_piped_install_has_no_unbound_source_and_ignores_cwd_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp) / "installer_wizard"
            planted.mkdir()
            (planted / "bootstrap.sh").write_text("echo PLANTED\n", encoding="utf-8")
            env = dict(os.environ, HTTPS_PROXY="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
                       NO_PROXY="", no_proxy="", NUXIVA_LANG="en")
            result = subprocess.run(
                ["bash"], input=INSTALL.read_text(encoding="utf-8"), cwd=tmp,
                capture_output=True, text=True, env=env, timeout=60,
            )
        self.assertNotIn("BASH_SOURCE", result.stderr)
        self.assertNotIn("PLANTED", result.stdout)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
