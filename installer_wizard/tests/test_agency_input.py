import shutil
import subprocess
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "js" / "agency_input_check.js"


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class AgencyInputTest(unittest.TestCase):
    def test_keyboard_gesture_parity_and_typing_safety(self):
        done = subprocess.run(["node", str(CHECK)], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
