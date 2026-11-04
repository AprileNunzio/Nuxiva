import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import setup_api


class SetupReopenTest(unittest.TestCase):
    def test_reopen_clears_done_and_rotates_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "setup.json"
            target.write_text(json.dumps({"done": True}), encoding="utf-8")
            old_code = setup_api.guard.code
            with mock.patch.object(setup_api, "SETUP_FILE", target):
                self.assertTrue(setup_api.done())
                for _ in range(5):
                    setup_api.reopen("nunzio")
                    if setup_api.guard.code != old_code:
                        break
                self.assertFalse(setup_api.done())
                self.assertEqual(json.loads(target.read_text())["by"], "nunzio")
                self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)
            self.assertNotEqual(setup_api.guard.code, old_code)


if __name__ == "__main__":
    unittest.main()
