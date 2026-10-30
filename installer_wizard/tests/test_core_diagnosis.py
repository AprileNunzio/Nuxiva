import grp
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSIS = ROOT / "scripts" / "os" / "core_diagnosis.sh"


def run(nuxiva_dir: Path, script: str) -> subprocess.CompletedProcess:
    prelude = f'set -Eeuo pipefail\nfail() {{ echo "[FAIL] $*"; exit 1; }}\n. "{DIAGNOSIS}"\n'
    return subprocess.run(["bash", "-c", prelude + script], capture_output=True, text=True,
                          env={**os.environ, "NUXIVA_DIR": str(nuxiva_dir), "CORE_URL": "http://127.0.0.1:8443"})


@unittest.skipIf(os.name == "nt", "POSIX permission behavior is validated on Linux")
class CoreDiagnosisTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "Nuxiva"
        self.module = self.root / "server" / "cmd"
        self.module.mkdir(parents=True)
        self.source = self.module / "main.py"
        self.source.write_text("print('ok')\n", encoding="utf-8")
        self.source.chmod(0o600)
        for path in (self.module, self.module.parent):
            path.chmod(0o700)
        self.root.chmod(0o750)
        self.group = grp.getgrgid(os.getgid()).gr_name

    def tearDown(self):
        self.temporary.cleanup()

    def test_detects_code_cloned_with_restrictive_umask(self):
        self.assertEqual(run(self.root, f'core_code_unreadable "{self.group}"').returncode, 0)

    def test_grants_read_access_to_core_code(self):
        result = run(self.root, f'core_grant_code_access "{self.group}"; core_code_unreadable "{self.group}" || echo READABLE')
        self.assertIn("READABLE", result.stdout, result.stdout + result.stderr)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.module.stat().st_mode & 0o777, 0o750)

    def test_explains_illegal_instruction_and_out_of_memory(self):
        sigill = run(self.root, "core_reason_from_exit 132 false")
        oom = run(self.root, "core_reason_from_exit 0 true")
        normal = run(self.root, "core_reason_from_exit 1 false")
        self.assertIn("SIGILL", sigill.stdout)
        self.assertIn("RAM", oom.stdout)
        self.assertNotEqual(normal.returncode, 0)

    def test_failure_message_states_the_reason(self):
        result = run(self.root, 'core_cpu_hint() { :; }; core_fail "motivo di prova"')
        self.assertEqual(result.returncode, 1)
        self.assertIn("[FAIL] Nuxiva Core non risponde su http://127.0.0.1:8443/health: motivo di prova", result.stdout)


if __name__ == "__main__":
    unittest.main()
