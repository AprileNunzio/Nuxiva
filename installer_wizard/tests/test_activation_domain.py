import tempfile
import time
import unittest
from pathlib import Path

from features.activation.domain.errors import SequenceError
from features.activation.domain.journey import Journey, SequenceStatus, Stage
from features.activation.domain.sequence import Sequence, SequenceKind
from features.activation.domain.telemetry import TelemetryParser
from features.activation.infrastructure.journey_store import JourneyStore


class ActivationDomainTests(unittest.TestCase):
    def test_sequence_manifest_parsing(self):
        data = {
            "manifest_version": 1,
            "id": "neural_engine",
            "kind": "optional",
            "order": 100,
            "steps": ["ollama"],
            "icon": "icon.png",
            "choices": [
                {"id": "yes", "installs": True, "icon": "yes.png", "recommended": True},
                {"id": "no", "installs": False, "icon": "no.png"},
            ],
        }
        seq = Sequence.from_manifest(data)
        self.assertEqual(seq.id, "neural_engine")
        self.assertEqual(seq.kind, SequenceKind.OPTIONAL)
        self.assertEqual(len(seq.choices), 2)
        self.assertTrue(seq.awaits_user)

    def test_sequence_configure_kind(self):
        data = {
            "manifest_version": 1,
            "id": "setup_profile",
            "kind": "configure",
            "order": 200,
            "icon": "icon.png",
            "view": "view.js",
            "handler": "handler.py",
            "skippable": True,
        }
        seq = Sequence.from_manifest(data)
        self.assertEqual(seq.kind, SequenceKind.CONFIGURE)
        self.assertTrue(seq.awaits_user)
        self.assertTrue(seq.skippable)

    def test_sequence_validation_errors(self):
        with self.assertRaises(SequenceError):
            Sequence.from_manifest({"manifest_version": 1, "id": "invalid", "kind": "unknown", "order": 1})
        with self.assertRaises(SequenceError):
            Sequence.from_manifest({
                "manifest_version": 1,
                "id": "critical_opt",
                "kind": "optional",
                "order": 1,
                "critical": True,
                "steps": ["s1"],
                "choices": [
                    {"id": "y", "installs": True},
                    {"id": "n", "installs": False},
                ],
            })

    def test_journey_lifecycle(self):
        now = time.time()
        j = Journey.new(now)
        self.assertEqual(j.stage, Stage.NEW)
        self.assertEqual(j.percent(), 0.0)

        j.start(["preflight", "neural_engine"], now)
        self.assertEqual(j.stage, Stage.RUNNING)
        self.assertEqual(j.next_open(), "preflight")

        j.begin("preflight", now)
        self.assertEqual(j.current, "preflight")
        self.assertEqual(j.progress["preflight"].status, SequenceStatus.RUNNING)

        j.complete("preflight", now)
        self.assertEqual(j.progress["preflight"].status, SequenceStatus.DONE)
        self.assertEqual(j.percent(), 50.0)

        j.await_user("neural_engine", now)
        self.assertEqual(j.stage, Stage.AWAITING_USER)

        j.choose("neural_engine", "local", True, now)
        self.assertEqual(j.stage, Stage.RUNNING)
        self.assertEqual(j.progress["neural_engine"].choice, "local")

        j.begin("neural_engine", now)
        j.complete("neural_engine", now)
        self.assertEqual(j.percent(), 100.0)

        j.finish(now)
        self.assertEqual(j.stage, Stage.DONE)

    def test_journey_persistence_atomic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "state" / "activation.json"
            store = JourneyStore(file_path)
            self.assertFalse(store.exists())
            self.assertIsNone(store.load())

            now = 1000.0
            j = Journey.new(now)
            j.start(["s1"], now)
            store.save(j)

            self.assertTrue(store.exists())
            loaded = store.load()
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.stage, Stage.RUNNING)
            self.assertEqual(loaded.order, ["s1"])
            self.assertEqual(loaded.revision, 1)

    def test_telemetry_parser(self):
        parsed = TelemetryParser.parse_line("@@PROGRESS 45 Scaricamento modelli neurali")
        self.assertEqual(parsed.get("progress"), 45.0)
        self.assertEqual(parsed.get("message"), "Scaricamento modelli neurali")

        parsed_speed = TelemetryParser.parse_line("@@SPEED 12.5 MB/s")
        self.assertEqual(parsed_speed.get("speed"), "12.5 MB/s")

        parsed_fallback = TelemetryParser.parse_line("Progress: 80% at 5.2 MiB/s")
        self.assertEqual(parsed_fallback.get("progress"), 80.0)
        self.assertEqual(parsed_fallback.get("speed"), "5.2 MiB/s")


if __name__ == "__main__":
    unittest.main()
