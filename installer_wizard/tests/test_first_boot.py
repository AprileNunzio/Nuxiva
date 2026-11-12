import json
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIRST_BOOT = ROOT / "installer_wizard" / "first_boot.sh"
BOOTSTRAP = ROOT / "installer_wizard" / "bootstrap.sh"
GATE = ROOT / "installer_wizard" / "reboot_gate.sh"
WATCH = ROOT / "scripts" / "os" / "kiosk" / "watch.sh"
KIOSK_STEP = ROOT / "scripts" / "os" / "steps" / "25-kiosk.sh"
SCREEN_UNIT = ROOT / "scripts" / "os" / "systemd" / "nuxiva-screen.service"
ENV_TOOL = ROOT / "installer_wizard" / "backend" / "env_format.py"
LANG_DIR = ROOT / "installer_wizard" / "bootstrap_language"
NEW_KEYS = ("reboot_count", "reboot_cancel", "kiosk_setup", "no_screen", "verify_fail")

PRELUDE = """
declare -A T=([reboot_wait]=wait [reboot_now]=now [reboot_deferred]="deferred %s" [reboot_manual]=manual
              [reboot_count]="count %s" [reboot_cancel]=cancelled [no_screen]=noscreen [verify_fail]="verify %s")
C_RED= C_OFF= C_AMBER= C_CYAN= G_BAD=x G_RUN=r G_DOT=. TTY=0
fmt_dur() { printf -v "$1" '%ss' "$2"; }
"""


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "bash and jq required")
class FirstBootTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nuxiva-first-boot-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.calls = self.tmp / "calls.log"
        self.drm = self.tmp / "drm"
        self.drm.mkdir()
        self.env_file = self.tmp / "nuxiva.env"
        self.setup_file = self.tmp / "setup.json"
        self.getty = self.tmp / "override.conf"
        self.wiz = self.tmp / "wiz"
        self.wiz.mkdir()
        shutil.copy(GATE, self.wiz / "reboot_gate.sh")
        self.stub("systemctl", f'printf "systemctl %s\\n" "$*" >> "{self.calls}"\nexit "${{SYSTEMCTL_RC:-0}}"')
        self.stub("systemd-run", f'printf "systemd-run %s\\n" "$*" >> "{self.calls}"')
        self.stub("sleep", f'printf "sleep %s\\n" "$*" >> "{self.calls}"')
        self.stub("pgrep", "exit 1")
        self.stub("busctl", "exit 1")

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def screen(self, status):
        (self.drm / "card0-HDMI-A-1").mkdir(exist_ok=True)
        (self.drm / "card0-HDMI-A-1" / "status").write_text(status + "\n", encoding="utf-8")

    def run_fb(self, script, **extra):
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.tmp),
            "FIRST_BOOT_DRM_GLOB": f"{self.drm}/card*-*/status",
            "FIRST_BOOT_FB": str(self.tmp / "fb0"),
            "FIRST_BOOT_ENV": str(self.env_file),
            "FIRST_BOOT_SETUP": str(self.setup_file),
            "FIRST_BOOT_GETTY": str(self.getty),
            "FIRST_BOOT_TTY": str(self.tmp / "no-tty"),
            "REBOOT_GATE_LOCKS": str(self.tmp / "missing-lock"),
            "WIZ": str(self.wiz),
            "LOG": str(self.tmp / "bootstrap.log"),
            "SYSTEMCTL_RC": "0",
        }
        env.update(extra)
        return subprocess.run(
            ["bash", "-c", f'set -Eeuo pipefail\n{PRELUDE}\nsource "{FIRST_BOOT}"\n{script}'],
            capture_output=True, text=True, env=env, timeout=30,
        )

    def calls_made(self):
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def test_kiosk_is_enabled_by_default(self):
        self.assertEqual(self.run_fb("first_boot_kiosk_choice").stdout.strip(), "1")

    def test_old_default_zero_does_not_survive_a_fresh_install(self):
        self.env_file.write_text("NUXIVA_KIOSK=0\n", encoding="utf-8")
        self.assertEqual(self.run_fb("first_boot_kiosk_choice").stdout.strip(), "1")

    def test_choice_made_in_completed_setup_is_kept(self):
        self.env_file.write_text("NUXIVA_KIOSK=0\n", encoding="utf-8")
        self.setup_file.write_text(json.dumps({"done": True}), encoding="utf-8")
        self.assertEqual(self.run_fb("first_boot_kiosk_choice").stdout.strip(), "0")

    def test_explicit_environment_wins(self):
        self.assertEqual(self.run_fb("first_boot_kiosk_choice", NUXIVA_KIOSK="off").stdout.strip(), "0")

    def test_set_env_writes_a_valid_value_and_rejects_injection(self):
        result = self.run_fb(f'first_boot_set_env NUXIVA_KIOSK 1 "{ENV_TOOL}"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(self.env_file.read_text(encoding="utf-8"), r"(?m)^NUXIVA_KIOSK=\"?1\"?$")
        bad = self.run_fb(f'first_boot_set_env NUXIVA_KIOSK "1; reboot" "{ENV_TOOL}"')
        self.assertEqual(bad.returncode, 64)

    def test_screen_detection(self):
        self.assertNotEqual(self.run_fb("first_boot_screen").returncode, 0)
        self.screen("disconnected")
        self.assertNotEqual(self.run_fb("first_boot_screen").returncode, 0)
        self.screen("connected")
        self.assertEqual(self.run_fb("first_boot_screen").returncode, 0)

    def test_countdown_without_terminal_never_waits_for_input(self):
        result = self.run_fb('first_boot_countdown 10 "count %s"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("count 10", result.stderr)
        self.assertEqual(self.calls_made(), ["sleep 10"])

    def test_verify_reports_what_is_missing(self):
        result = self.run_fb("first_boot_verify 0", SYSTEMCTL_RC="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nuxiva-supervisor.service (enabled)", result.stdout)
        result = self.run_fb("first_boot_verify 1")
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(self.getty), result.stdout)

    def test_restart_reboots_when_screen_is_connected(self):
        self.screen("connected")
        self.getty.write_text("[Service]\n", encoding="utf-8")
        self.stub("chromium", "exit 0")
        self.stub("startx", "exit 0")
        result = self.run_fb("KIOSK=1; restart_when_idle")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("now", result.stdout)
        self.assertIn("systemctl reboot -i", self.calls_made())

    def test_restart_skipped_without_screen_with_clear_message(self):
        self.getty.write_text("[Service]\n", encoding="utf-8")
        self.stub("chromium", "exit 0")
        self.stub("startx", "exit 0")
        result = self.run_fb("KIOSK=1; restart_when_idle")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("noscreen", result.stdout)
        self.assertNotIn("systemctl reboot -i", self.calls_made())

    def test_restart_fails_honestly_when_kiosk_is_incomplete(self):
        self.screen("connected")
        result = self.run_fb("KIOSK=1; restart_when_idle")
        self.assertEqual(result.returncode, 1)
        self.assertIn("verify", result.stdout)
        self.assertNotIn("systemctl reboot -i", self.calls_made())


@unittest.skipUnless(shutil.which("bash"), "bash required")
class ScreenWatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nuxiva-watch-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.calls = self.tmp / "calls.log"
        self.drm = self.tmp / "drm" / "card0-HDMI-A-1"
        self.drm.mkdir(parents=True)
        self.env_file = self.tmp / "nuxiva.env"
        self.env_file.write_text("NUXIVA_KIOSK=1\nNUXIVA_KIOSK_USER=root\n", encoding="utf-8")
        self.getty = self.tmp / "override.conf"
        self.getty.write_text("[Service]\n", encoding="utf-8")
        counter = self.tmp / "ticks"
        counter.write_text("0", encoding="utf-8")
        self.stub("systemctl", f'printf "systemctl %s\\n" "$*" >> "{self.calls}"')
        self.stub("pgrep", "exit 1")
        self.stub("ps", "exit 1")
        self.stub("sleep", f'n=$(cat "{counter}"); echo $((n + 1)) > "{counter}"; [ "$n" -lt 2 ] || kill -TERM "$PPID"')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def run_watch(self, status):
        (self.drm / "status").write_text(status + "\n", encoding="utf-8")
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "NUXIVA_ENV_FILE": str(self.env_file),
            "NUXIVA_GETTY_OVERRIDE": str(self.getty),
            "NUXIVA_DRM_GLOB": f"{self.tmp}/drm/card*-*/status",
        }
        result = subprocess.run(["bash", str(WATCH)], capture_output=True, text=True, env=env, timeout=30)
        calls = self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []
        return result, calls

    def test_starts_kiosk_when_screen_is_connected(self):
        result, calls = self.run_watch("connected")
        self.assertIn("Screen connected", result.stdout)
        self.assertIn("systemctl restart getty@tty1.service", calls)

    def test_stays_on_standby_without_screen(self):
        result, calls = self.run_watch("disconnected")
        self.assertIn("No screen", result.stdout)
        self.assertEqual(calls, [])


class FirstBootWiringTest(unittest.TestCase):
    def test_bootstrap_enables_kiosk_and_never_writes_zero_default(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn('echo "NUXIVA_KIOSK=0"', text)
        self.assertIn("first_boot_kiosk_choice", text)
        self.assertIn("25-kiosk.sh\" apply", text)
        for key in NEW_KEYS:
            self.assertEqual(text.count(f"[{key}]="), 2, key)

    def test_every_language_file_has_the_new_texts(self):
        for name in (LANG_DIR / "index.txt").read_text(encoding="utf-8").split():
            keys = {line.split("=", 1)[0] for line in (LANG_DIR / f"{name}.txt").read_text(encoding="utf-8").splitlines()}
            for key in NEW_KEYS:
                self.assertIn(key, keys, f"{name}: {key}")

    def test_kiosk_step_installs_the_hardened_screen_service(self):
        step = KIOSK_STEP.read_text(encoding="utf-8")
        self.assertIn("nuxiva-screen.service", step)
        unit = SCREEN_UNIT.read_text(encoding="utf-8")
        for line in ("NoNewPrivileges=yes", "ProtectSystem=strict", "PrivateNetwork=yes", "CapabilityBoundingSet=",
                     "Restart=always", "WantedBy=multi-user.target", "ExecStart=/bin/bash /opt/Nuxiva/scripts/os/kiosk/watch.sh"):
            self.assertIn(line, unit)


if __name__ == "__main__":
    unittest.main()
