import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

EAR = Path(__file__).resolve().parents[1] / "features" / "ear"
if str(EAR) not in sys.path:
    sys.path.append(str(EAR))

import learner as learner_module


class WakeNameTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.file = Path(self.dir.name) / "learn.json"
        self.old = learner_module.LEARN_FILE
        learner_module.LEARN_FILE = self.file

    def tearDown(self):
        learner_module.LEARN_FILE = self.old
        self.dir.cleanup()

    def test_ehi_nuxiva_wakes_and_leaves_the_command(self):
        learner = learner_module.Learner()
        for text in ("Ehi, Nuxiva, accendi la luce", "ehi nuxiva accendi la luce", "Nuxiva accendi la luce",
                     "Hey Nuxiva, accendi la luce"):
            with self.subTest(text=text):
                start, end, _ = learner.find_wake(text)
                self.assertEqual(text[end:], "accendi la luce")

    def test_split_name_and_more_greetings_wake_and_leave_the_command(self):
        learner = learner_module.Learner()
        for text in ("nu xiva, accendi la luce", "Nu xiva accendi la luce", "Hei Nuxiva accendi la luce",
                     "E Nuxiva, accendi la luce", "Eh nuxiva accendi la luce"):
            with self.subTest(text=text):
                found = learner.find_wake(text)
                self.assertIsNotNone(found)
                self.assertEqual(text[found[1]:], "accendi la luce")
        for text in ("la tenda è rotta", "e la catena del cancello"):
            with self.subTest(text=text):
                self.assertIsNone(learner.find_wake(text))

    def test_close_mishearing_wakes_but_common_words_do_not(self):
        learner = learner_module.Learner()
        self.assertIsNotNone(learner.find_wake("Nuxiba accendi la luce"))
        for text in ("catena del cancello", "arena di Verona", "Serena accendi la luce"):
            with self.subTest(text=text):
                self.assertIsNone(learner.find_wake(text))
        self.assertFalse(learner.learn_variant("catena"))

    def test_variants_learned_for_another_name_are_dropped(self):
        self.file.write_text(json.dumps({"variants": {"marvin": 5}, "strict": False}), encoding="utf-8")
        learner = learner_module.Learner()
        self.assertEqual(learner.data["variants"], {})
        self.assertIsNone(learner.find_wake("marvin accendi la luce"))
        self.assertEqual(learner.hotwords().split()[0], "Nuxiva")

    def test_custom_assistant_name_wakes_both_with_and_without_hey(self):
        with mock.patch.dict(os.environ, {"NUXIVA_ASSISTANT_NAME": "Jarvis"}):
            learner = learner_module.Learner()
            for text in ("Jarvis, accendi la luce", "Hey Jarvis, accendi la luce", "Ehi Jarvis accendi la luce", "jarvis accendi la luce"):
                with self.subTest(text=text):
                    found = learner.find_wake(text)
                    self.assertIsNotNone(found)
                    self.assertEqual(text[found[1]:], "accendi la luce")

    def test_wake_model_name_is_validated(self):
        import importlib
        os.environ["NUXIVA_WAKEWORD_MODEL"] = "../../etc/passwd"
        try:
            wakeword = importlib.import_module("wakeword")
            self.assertEqual(wakeword.model_name(), "ehi_nuxiva")
            os.environ["NUXIVA_WAKEWORD_MODEL"] = "ehi_nuxiva_v2"
            self.assertEqual(wakeword.model_name(), "ehi_nuxiva_v2")
        finally:
            os.environ.pop("NUXIVA_WAKEWORD_MODEL", None)


if __name__ == "__main__":
    unittest.main()
