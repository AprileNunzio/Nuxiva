import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PERMISSIONS = ROOT / "scripts" / "os" / "kiosk" / "permissions.sh"


class KioskPermissionsTest(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX permission behavior is validated on Linux")
    def test_repairs_only_required_script_paths_and_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            os_root = scripts / "os"
            kiosk = os_root / "kiosk"
            steps = os_root / "steps"
            kiosk.mkdir(parents=True)
            steps.mkdir()
            files = [kiosk / "session.sh", kiosk / "launch.sh", os_root / "nuxivactl", os_root / "25.sh",
                     steps / "25-kiosk.sh"]
            for path in files:
                path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
                path.chmod(0o600)
            for path in (scripts, os_root, kiosk):
                path.chmod(0o700)
            root.chmod(0o750)
            subprocess.run(["bash", str(PERMISSIONS)], check=True, env={**os.environ, "NUXIVA_DIR": str(root)})
            self.assertEqual(root.stat().st_mode & 0o777, 0o751)
            self.assertTrue(all(path.stat().st_mode & 0o111 for path in files))
            self.assertEqual(scripts.stat().st_mode & 0o777, 0o755)
            self.assertEqual(os_root.stat().st_mode & 0o777, 0o755)
            self.assertEqual(kiosk.stat().st_mode & 0o777, 0o755)
            self.assertEqual(steps.stat().st_mode & 0o777, 0o755)

    @unittest.skipIf(os.name == "nt", "POSIX script execution is validated on Linux")
    def test_fails_when_required_kiosk_script_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts/os/kiosk").mkdir(parents=True)
            result = subprocess.run(["bash", str(PERMISSIONS)], env={**os.environ, "NUXIVA_DIR": str(root)},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Script kiosk Nuxiva mancante", result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX symlink behavior is validated on Linux")
    def test_refuses_symlinked_kiosk_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "nuxiva"
            kiosk = root / "scripts/os/kiosk"
            kiosk.mkdir(parents=True)
            target = Path(temporary) / "evil.sh"
            target.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            target.chmod(0o600)
            (kiosk / "session.sh").symlink_to(target)
            for path in (kiosk / "launch.sh", root / "scripts/os/nuxivactl"):
                path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            result = subprocess.run(["bash", str(PERMISSIONS)], env={**os.environ, "NUXIVA_DIR": str(root)},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("link simbolico", result.stderr)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
