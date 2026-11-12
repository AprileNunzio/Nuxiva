import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "os" / "units.sh"

FAKE_SYSTEMCTL = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_LOG"
has() { case " $1 " in *" $2 "*) return 0 ;; esac; return 1; }
last="${@: -1}"
case "$1" in
    is-enabled) has "$FAKE_ENABLED" "$last" ;;
    is-active) has "$FAKE_ACTIVE" "$last" ;;
    show)
        if [ "$3" = Type ]; then
            if has "$FAKE_ONESHOT" "$last"; then echo oneshot; else echo simple; fi
        elif [ "$3" = ActiveState ]; then
            if has "$FAKE_ACTIVATING" "$last"; then echo activating; else echo inactive; fi
        fi ;;
    daemon-reload) [ "${FAKE_RELOAD_FAILS:-0}" = 0 ] ;;
    *) exit 0 ;;
esac
"""


def unit(exec_start: str) -> str:
    return f"[Unit]\nDescription=test\n\n[Service]\nExecStart={exec_start}\n\n[Install]\nWantedBy=multi-user.target\n"


class UnitSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.src, self.dst, self.bin = root / "src", root / "dst", root / "bin"
        for d in (self.src, self.dst, self.bin):
            d.mkdir()
        self.log = root / "systemctl.log"
        fake = self.bin / "systemctl"
        fake.write_text(FAKE_SYSTEMCTL)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.src.joinpath("nuxiva-supervisor.service").write_text(unit("/opt/Nuxiva/sup"))
        self.src.joinpath("nuxiva-rollback.service").write_text("[Service]\nType=oneshot\nExecStart=/bin/true\n")
        self.dst.joinpath("nuxiva-supervisor.service").write_text(unit("/opt/Nuxiva/sup"))
        self.dst.joinpath("nuxiva-rollback.service").write_text("[Service]\nType=oneshot\nExecStart=/bin/true\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_sync(self, **fake: str) -> subprocess.CompletedProcess:
        env = {"PATH": f"{self.bin}:{os.environ['PATH']}", "FAKE_LOG": str(self.log), "LANG": "en",
               "FAKE_ENABLED": "", "FAKE_ACTIVE": "", "FAKE_ONESHOT": "nuxiva-rollback.service", "FAKE_ACTIVATING": ""}
        env.update(fake)
        return subprocess.run(["bash", str(SCRIPT), str(self.src), str(self.dst)], env=env,
                              capture_output=True, text=True, timeout=60)

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_stale_installed_unit_is_replaced_reloaded_and_restarted(self):
        self.src.joinpath("nuxiva-vision.service").write_text(unit("/opt/Nuxiva/installer_wizard/agenti/percezione/vision/service.py"))
        self.dst.joinpath("nuxiva-vision.service").write_text(unit("/opt/Nuxiva/installer_wizard/features/vision/service.py"))
        result = self.run_sync(FAKE_ENABLED="nuxiva-vision.service")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("agenti/percezione/vision", self.dst.joinpath("nuxiva-vision.service").read_text())
        self.assertEqual(stat.S_IMODE(self.dst.joinpath("nuxiva-vision.service").stat().st_mode), 0o644)
        calls = self.calls()
        self.assertEqual(calls.count("daemon-reload"), 1)
        self.assertIn("reset-failed nuxiva-vision.service", calls)
        self.assertIn("restart --no-block nuxiva-vision.service", calls)
        self.assertLess(calls.index("daemon-reload"), calls.index("restart --no-block nuxiva-vision.service"))
        self.assertEqual(list(self.dst.glob(".nuxiva-unit.*")), [])

    def test_crash_looping_unit_is_restarted_even_if_not_enabled(self):
        self.src.joinpath("nuxiva-voice.service").write_text(unit("/new"))
        self.dst.joinpath("nuxiva-voice.service").write_text(unit("/old"))
        self.run_sync(FAKE_ACTIVATING="nuxiva-voice.service")
        self.assertIn("restart --no-block nuxiva-voice.service", self.calls())

    def test_disabled_unit_is_updated_but_not_started(self):
        self.src.joinpath("nuxiva-core.service").write_text(unit("/new"))
        self.dst.joinpath("nuxiva-core.service").write_text(unit("/old"))
        self.run_sync()
        self.assertIn("/new", self.dst.joinpath("nuxiva-core.service").read_text())
        self.assertFalse(any(c.startswith("restart") for c in self.calls()))

    def test_components_never_installed_stay_absent(self):
        self.src.joinpath("nuxiva-ear.service").write_text(unit("/ear"))
        result = self.run_sync()
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.dst.joinpath("nuxiva-ear.service").exists())
        self.assertNotIn("daemon-reload", self.calls())

    def test_required_units_are_installed_but_supervisor_and_oneshot_are_not_restarted(self):
        self.dst.joinpath("nuxiva-rollback.service").unlink()
        self.src.joinpath("nuxiva-supervisor.service").write_text(unit("/opt/Nuxiva/sup2"))
        self.run_sync(FAKE_ENABLED="nuxiva-supervisor.service nuxiva-rollback.service")
        self.assertTrue(self.dst.joinpath("nuxiva-rollback.service").exists())
        self.assertIn("sup2", self.dst.joinpath("nuxiva-supervisor.service").read_text())
        self.assertFalse(any(c.startswith("restart") for c in self.calls()))

    def test_masked_unit_is_left_alone(self):
        self.src.joinpath("nuxiva-vision.service").write_text(unit("/new"))
        self.dst.joinpath("nuxiva-vision.service").symlink_to("/dev/null")
        self.run_sync(FAKE_ENABLED="nuxiva-vision.service")
        self.assertEqual(os.readlink(self.dst / "nuxiva-vision.service"), "/dev/null")
        self.assertNotIn("daemon-reload", self.calls())

    def test_invalid_source_is_refused(self):
        self.src.joinpath("nuxiva-vision.service").write_text("[Unit]\nDescription=broken\n")
        self.dst.joinpath("nuxiva-vision.service").write_text(unit("/old"))
        result = self.run_sync(FAKE_ENABLED="nuxiva-vision.service")
        self.assertEqual(result.returncode, 1)
        self.assertIn("/old", self.dst.joinpath("nuxiva-vision.service").read_text())

    def test_untrusted_names_are_ignored(self):
        self.src.joinpath("nuxiva-Evil name.service").write_text(unit("/evil"))
        self.dst.joinpath("nuxiva-Evil name.service").write_text(unit("/old"))
        self.run_sync()
        self.assertIn("/old", self.dst.joinpath("nuxiva-Evil name.service").read_text())

    def test_reload_failure_skips_restarts_and_reports(self):
        self.src.joinpath("nuxiva-vision.service").write_text(unit("/new"))
        self.dst.joinpath("nuxiva-vision.service").write_text(unit("/old"))
        result = self.run_sync(FAKE_ENABLED="nuxiva-vision.service", FAKE_RELOAD_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(any(c.startswith("restart") for c in self.calls()))

    def test_up_to_date_system_does_nothing(self):
        result = self.run_sync()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])


class RepositoryUnitsTest(unittest.TestCase):
    def test_every_shipped_unit_points_to_files_that_exist(self):
        root = SCRIPT.parents[2]
        units = sorted((root / "scripts" / "os" / "systemd").glob("nuxiva-*.service"))
        self.assertTrue(units)
        for path in units:
            for match in re.findall(r"/opt/Nuxiva/(\S+?\.(?:py|sh))\b", path.read_text()):
                self.assertTrue((root / match).is_file(), f"{path.name}: {match}")


if __name__ == "__main__":
    unittest.main()
