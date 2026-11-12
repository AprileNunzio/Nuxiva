import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center import boot

ROOT = Path(__file__).resolve().parents[2]


class BootViewTest(unittest.TestCase):
    def test_idle_phases_hide_boot(self):
        self.assertIsNone(boot.view(SimpleNamespace(current_step="native", phase="READY", steps={}, detail="")))
        self.assertIsNone(boot.view(SimpleNamespace(current_step="", phase="BOOTING", steps={}, detail="")))

    def test_running_step_is_reported_and_sanitized(self):
        store = SimpleNamespace(current_step="native", phase="BOOTING", detail="Compiling pyo3\x1b[0m v0.27",
                                steps={"native": {"progress": 140, "message": "Compilazione · 47/143", "last_update": 100.0}})
        out = boot.view(store, now=250.0)
        self.assertEqual(out["step"], "native")
        self.assertEqual(out["title"], "Core nativo")
        self.assertEqual(out["progress"], 100)
        self.assertEqual(out["detail"], "Compiling pyo3[0m v0.27")
        self.assertEqual(out["silent_for"], 150.0)


class CargoStreamTest(unittest.TestCase):
    def test_stream_reports_progress_and_exit_code(self):
        script = f"""
progress() {{ echo "@@PROGRESS $1 ${{*:2}}"; }}
detail() {{ echo "@@DETAIL $*"; }}
info() {{ echo "[INFO] $*"; }}
warn() {{ echo "[WARN] $*"; }}
NATIVE_SRC=/nonexistent
. "{ROOT}/scripts/os/lib_build.sh"
fake() {{ printf '   Compiling alpha v1.0\\n   Compiling beta v2.0\\nerror: boom\\n'; return 3; }}
cargo_stream "Prova" 50 74 pkg fake
echo "rc=$?"
"""
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run(["bash", "-c", script], cwd=tmp, capture_output=True, text=True, timeout=30).stdout
        self.assertIn("@@DETAIL Compiling alpha v1.0", out)
        self.assertIn("@@PROGRESS 50 Prova · 2/? ·", out)
        self.assertIn("[WARN] error: boom", out)
        self.assertIn("rc=3", out)


if __name__ == "__main__":
    unittest.main()
