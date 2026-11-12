import tempfile
import time
import unittest
from pathlib import Path

from agenti.activation.application.advance_journey import AdvanceJourneyUseCase
from agenti.activation.domain.journey import Journey, SequenceStatus, Stage
from agenti.activation.infrastructure.journey_store import JourneyStore
from agenti.activation.infrastructure.sequence_catalog import SequenceCatalog
from agenti.activation.infrastructure.step_runner import StepRunner


class AdvanceJourneyTests(unittest.IsolatedAsyncioTestCase):
    async def test_advance_stops_at_optional_and_resumes_after_choice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JourneyStore(Path(tmpdir) / "activation.json")
            catalog_dir = Path(tmpdir) / "sequences"
            catalog_dir.mkdir()

            s1_dir = catalog_dir / "s1"
            s1_dir.mkdir()
            (s1_dir / "sequence.json").write_text(
                '{"manifest_version": 1, "id": "s1", "kind": "mandatory", "order": 10, "steps": ["step1"]}',
                encoding="utf-8",
            )

            s2_dir = catalog_dir / "s2"
            s2_dir.mkdir()
            (s2_dir / "sequence.json").write_text(
                '{"manifest_version": 1, "id": "s2", "kind": "optional", "order": 20, "steps": ["step2"], "choices": [{"id": "yes", "installs": true}, {"id": "no", "installs": false}]}',
                encoding="utf-8",
            )

            catalog = SequenceCatalog(catalog_dir)
            catalog.scan()

            executed_steps = []

            async def fake_run(step_id, action, cb):
                executed_steps.append((step_id, action))
                cb("@@PROGRESS 100 Done")
                return 0, ""

            runner = StepRunner(fake_run)
            env_written = {}

            def write_env(d):
                env_written.update(d)

            now = time.time()
            journey = Journey.new(now)
            journey.start(["s1", "s2"], now)
            store.save(journey)

            use_case = AdvanceJourneyUseCase(store, catalog, runner, write_env)

            j = await use_case.execute()
            self.assertEqual(j.stage, Stage.AWAITING_USER)
            self.assertEqual(j.current, "s2")
            self.assertEqual(j.progress["s1"].status, SequenceStatus.DONE)
            self.assertEqual(executed_steps, [("step1", "apply")])

            j.choose("s2", "yes", True, time.time())
            store.save(j)

            j2 = await use_case.execute()
            self.assertEqual(j2.stage, Stage.DONE)
            self.assertEqual(j2.progress["s2"].status, SequenceStatus.DONE)
            self.assertEqual(executed_steps, [("step1", "apply"), ("step2", "apply")])


if __name__ == "__main__":
    unittest.main()
