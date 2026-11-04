import shutil
import subprocess
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "js" / "gesture_check.js"
EVENTS = Path(__file__).resolve().parent / "js" / "hands_events_check.js"


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class HandGestureMathTest(unittest.TestCase):
    def test_gesture_math(self):
        result = subprocess.run(["node", str(CHECK)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_engine_events_drive_display(self):
        result = subprocess.run(["node", str(EVENTS)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)
