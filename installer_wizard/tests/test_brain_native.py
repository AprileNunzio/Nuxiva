import json
import tempfile
import unittest
from pathlib import Path

import native_core

ROOT = Path(__file__).resolve().parents[1] / "agenti"


@unittest.skipUnless(native_core.symbol("RustBrain") is not None, "modulo nativo assente")
class RustBrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = native_core.symbol("RustMcpEngine")("{}", "{}", str(Path(self.tmp.name) / "audit.log"), 0)
        self.addCleanup(self.engine.shutdown)

    def test_conversation_and_rejections(self):
        brain = native_core.symbol("RustBrain")(self.engine, str(ROOT), None)
        self.assertEqual(json.loads(brain.dispatch("ciao come stai", "nunzio", 1)), {"kind": "conversation"})
        with self.assertRaises(ValueError):
            brain.dispatch("", "nunzio", 1)
        with self.assertRaises(ValueError):
            brain.dispatch("accendi\x00luce", "nunzio", 1)
        brain.cancel()

    def test_missing_agents_directory_is_an_error(self):
        with self.assertRaises(ValueError):
            native_core.symbol("RustBrain")(self.engine, str(Path(self.tmp.name) / "assente"), None)

    def test_planner_callback_is_accepted(self):
        calls = []
        brain = native_core.symbol("RustBrain")(self.engine, str(ROOT), lambda prompt: calls.append(prompt) or "{}")
        self.assertEqual(json.loads(brain.dispatch("ciao come stai", "guest", 2)), {"kind": "conversation"})


if __name__ == "__main__":
    unittest.main()
