import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import native_core

from agenti.chat import personal_memory
from personal_graph import PersonalGraph
from personal_graph.fallback import PyGraph


def run(coro):
    return asyncio.run(coro)


class DisabledByDefaultTest(unittest.TestCase):
    def test_off_without_flag(self):
        with mock.patch.dict(os.environ, {"NUXIVA_KNOWLEDGE": "off"}):
            self.assertFalse(personal_memory.enabled())
            self.assertEqual(personal_memory.recall("nunzio", "family", "caffè"), [])
            self.assertIsNone(run(personal_memory.learn("nunzio", "family", "mi piace il caffè")))

    def test_system_and_unknown_speakers_are_not_eligible(self):
        with mock.patch.object(personal_memory, "available", return_value=True):
            self.assertFalse(personal_memory.eligible("", "family"))
            self.assertFalse(personal_memory.eligible("nunzio", "system"))
            self.assertTrue(personal_memory.eligible("nunzio", "family"))


class GlueWithFallbackEngineTest(unittest.TestCase):
    def setUp(self):
        personal_memory.reset()
        fake = PersonalGraph(PyGraph())
        patches = [
            mock.patch.dict(os.environ, {"NUXIVA_KNOWLEDGE": "on"}),
            mock.patch.object(personal_memory, "available", return_value=True),
            mock.patch.object(personal_memory, "graph", return_value=fake),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(personal_memory.reset)

    def test_recall_never_raises_and_learn_never_blocks_chat(self):
        self.assertEqual(personal_memory.recall("nunzio", "family", "caffè"), [])
        self.assertIsNone(run(personal_memory.learn("nunzio", "family", "mi piace il caffè")))


@unittest.skipIf(native_core.symbol("RustKnowledge") is None, "modulo nativo assente")
class NativeEndToEndTest(unittest.TestCase):
    def test_learn_recall_and_encrypted_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            etc, state = Path(tmp) / "etc", Path(tmp) / "state"
            etc.mkdir()
            personal_memory.reset()
            with mock.patch.dict(os.environ, {"NUXIVA_KNOWLEDGE": "on"}), \
                    mock.patch.object(personal_memory, "ETC_DIR", etc), \
                    mock.patch.object(personal_memory, "STATE_DIR", state):
                run(personal_memory.learn("nunzio", "family", "Abito a Bologna e mi piace il caffè"))
                lines = personal_memory.recall("nunzio", "family", "Bologna")
                self.assertTrue(any("Bologna" in line for line in lines))
                blobs = [p for p in (state / "knowledge").iterdir() if p.suffix == ".nkg"]
                self.assertTrue(blobs)
                self.assertNotIn(b"Bologna", blobs[0].read_bytes())
                self.assertEqual((etc / "knowledge.key").stat().st_mode & 0o777, 0o600)
                personal_memory.reset()
                again = personal_memory.recall("nunzio", "family", "Bologna")
                self.assertTrue(any("Bologna" in line for line in again))
            personal_memory.reset()


if __name__ == "__main__":
    unittest.main()
