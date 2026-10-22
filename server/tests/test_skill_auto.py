import asyncio
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from server.core.core_platform.result import Ok
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.contracts import ArbiterThresholds
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository
from server.core.plasticity import scheduler
from server.core.plasticity.auto_training import AutoTrainer
from server.core.plasticity.ledger import PlasticityLedger
from server.core.plasticity.service import PlasticityService
from server.core.skill_forge import author, mining
from server.core.skill_forge.auto import AutoForge, AutoLimits
from server.core.skill_forge.forge import SkillForge, SkillRuntime
from server.core.skill_forge.misses import MissLedger
from server.core.skill_forge.store import SkillStore
from server.tests.cortex_support import SECRET, requires_native
from server.tests.test_skill_forge import GOOD, FixedExtractor, HashEmbedder, manifest

REQUESTS = [f"converti {n} gradi celsius in fahrenheit" for n in (10, 15, 20, 25, 30, 35)]
SOURCE = (
    "def run(slots):\n"
    "    value = float(slots['value'])\n"
    "    return {'speech': str(round(value * 9 / 5 + 32)) + ' gradi fahrenheit'}\n"
)
AUTHORED = {
    "forgeable": True, "neuron_id": "convert.celsius", "title": "Celsius in Fahrenheit",
    "slot_schema": [{"name": "value", "entity_label": "temperatura", "data_type": "number", "required": True}],
    "utterances": [f"converti {n} gradi celsius in fahrenheit" for n in range(1, 9)],
    "source": SOURCE,
    "cases": [{"slots": {"value": 0}, "expect_speech": "32 gradi fahrenheit"},
              {"slots": {"value": 100}, "expect_speech": "212 gradi fahrenheit"},
              {"slots": {"value": 37}, "expect_speech": "99 gradi fahrenheit"}],
}


def run(coroutine):
    return asyncio.run(coroutine)


class MiningTests(unittest.TestCase):
    def test_similar_requests_group_and_small_groups_are_dropped(self):
        vectors = [[1.0, 0.0]] * 5 + [[0.0, 1.0]] * 2
        texts = [f"a{i}" for i in range(5)] + ["b1", "b2"]
        groups = mining.cluster(texts, vectors)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 5)

    def test_key_is_stable_and_ignores_order_of_arrival_beyond_the_sample(self):
        self.assertEqual(mining.key(REQUESTS), mining.key(list(REQUESTS)))
        self.assertNotEqual(mining.key(REQUESTS), mining.key(["altra cosa"] * 6))


class AuthorTests(unittest.TestCase):
    def test_fenced_answer_is_parsed_and_id_is_namespaced(self):
        parsed = author.parse("```json\n" + json.dumps(AUTHORED) + "\n```")
        self.assertTrue(parsed.is_ok)
        self.assertEqual(parsed.value.manifest["neuron_id"], "auto.convert.celsius")
        self.assertEqual(parsed.value.source, SOURCE)

    def test_refusal_and_garbage_are_told_apart(self):
        self.assertIsNone(author.parse('{"forgeable": false}').value)
        self.assertEqual(author.parse("non lo so").error.code, "cortex.forge.author_invalid")
        thin = dict(AUTHORED, cases=AUTHORED["cases"][:1])
        self.assertEqual(author.parse(json.dumps(thin)).error.code, "cortex.forge.author_invalid")


@requires_native
class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "misses.db"
        self.ledger = MissLedger(self.path, ZeroTrustVault(lambda: SECRET))

    def test_requests_are_stored_sealed_and_settled(self):
        for text in REQUESTS:
            self.assertTrue(self.ledger.note(text).is_ok)
        raw = b"".join(row[0] for row in sqlite3.connect(self.path).execute("SELECT sealed FROM misses"))
        self.assertNotIn(b"celsius", raw)
        self.assertEqual(self.ledger.recent().value, REQUESTS)
        self.assertEqual(self.ledger.settled(REQUESTS[:2]).value, 2)
        self.assertEqual(self.ledger.count().value, 4)

    def test_expiry_and_attempt_memory(self):
        self.ledger.note("vecchia", now=1_000.0)
        self.ledger.note("nuova", now=10_000_000.0)
        self.assertEqual(self.ledger.expire(30, now=10_000_000.0).value, {"expired": 1})
        self.assertEqual(self.ledger.recent().value, ["nuova"])
        self.ledger.record_attempt("k", "forged", now=100.0)
        self.assertTrue(self.ledger.tried_recently("k", 7, now=100.0 + 86_400).value)
        self.assertFalse(self.ledger.tried_recently("k", 7, now=100.0 + 8 * 86_400).value)


@requires_native
class AutoForgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        vault = ZeroTrustVault(lambda: SECRET)
        self.store = SkillStore(root / "skills.sealed", vault)
        runtime = SkillRuntime(self.store)
        repository = EncryptedNeuronRepository(root / "neurons.sealed", vault)
        self.hippocampus = HippocampusService(HashEmbedder(), NeuronMemory(repository), ArbiterThresholds(),
                                              extractor=FixedExtractor(), executor=runtime, catalog=runtime)
        self.forge = SkillForge(self.hippocampus, self.store)
        self.ledger = MissLedger(root / "misses.db", vault)
        self.calls = []
        self.answer = json.dumps(AUTHORED)
        for text in REQUESTS:
            self.ledger.note(text)

    def auto(self, limits=AutoLimits()):
        async def complete(system, user):
            self.calls.append((system, user))
            if isinstance(self.answer, Exception):
                raise self.answer
            return self.answer

        return AutoForge(self.forge, self.hippocampus, self.ledger, complete, limits)

    def test_recurring_requests_become_a_verified_skill(self):
        report = run(self.auto().cycle()).value
        self.assertEqual(report["forged"], ["auto.convert.celsius"])
        listing = self.forge.listing().value
        self.assertEqual([(item["neuron_id"], item["origin"]) for item in listing], [("auto.convert.celsius", "forge")])
        self.assertEqual(self.ledger.count().value, 0)
        self.assertIn("converti 10 gradi celsius", self.calls[0][1])

    def test_a_skill_whose_own_cases_fail_is_not_adopted(self):
        wrong = json.loads(self.answer)
        wrong["cases"][0]["expect_speech"] = "33 gradi fahrenheit"
        self.answer = json.dumps(wrong)
        report = run(self.auto().cycle()).value
        self.assertEqual((report["forged"], report["rejected"]), ([], 1))
        self.assertEqual(self.forge.listing().value, [])
        self.assertEqual(self.ledger.count().value, len(REQUESTS))

    def test_dangerous_source_is_stopped_by_the_scanner(self):
        evil = dict(AUTHORED, source="import os\ndef run(slots):\n    return {'speech': os.getcwd()}\n")
        self.answer = json.dumps(evil)
        report = run(self.auto().cycle()).value
        self.assertEqual((report["forged"], report["rejected"]), ([], 1))
        self.assertEqual(self.forge.listing().value, [])

    def test_failed_clusters_are_not_retried_every_night(self):
        self.answer = '{"forgeable": false}'
        automatic = self.auto()
        run(automatic.cycle())
        second = run(automatic.cycle()).value
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(second["skipped"], 1)

    def test_unavailable_model_is_reported_not_hidden(self):
        self.answer = RuntimeError("down")
        report = run(self.auto().cycle()).value
        self.assertEqual(report["rejected"], 1)
        attempts = self.ledger.attempts().value
        self.assertEqual(attempts[0]["outcome"], "model_unavailable")

    def test_manual_skills_are_never_overwritten(self):
        taken = dict(AUTHORED, neuron_id="convert.celsius")
        self.forge.forge(manifest("auto.convert.celsius"), GOOD, "manual")
        self.answer = json.dumps(taken)
        report = run(self.auto().cycle()).value
        self.assertEqual(report["forged"], [])
        self.assertEqual(self.store.listing().value[0]["origin"], "manual")

    def test_per_cycle_budget_limits_model_calls(self):
        for text in [f"accendi la luce della stanza {n}" for n in range(6)]:
            self.ledger.note(text)
        self.answer = '{"forgeable": false}'
        run(self.auto(AutoLimits(per_cycle=1)).cycle())
        self.assertEqual(len(self.calls), 1)

    def test_pruned_forged_skill_is_retired_with_its_neuron(self):
        run(self.auto().cycle())
        plasticity = PlasticityLedger(Path(self.directory.name) / "plasticity.db", ZeroTrustVault(lambda: SECRET))
        service = PlasticityService(self.hippocampus, plasticity, retire=self.forge.retire)
        self.hippocampus.set_weight("auto.convert.celsius", 0.05)
        plasticity.touch("auto.convert.celsius", True, now=1.0)
        report = service.consolidate(now=1.0 + 200 * 86_400).value
        self.assertEqual(report["pruned"], ["auto.convert.celsius"])
        self.assertEqual(self.forge.listing().value, [])


class NightTests(unittest.TestCase):
    class Service:
        def consolidate(self):
            return Ok({"decayed": [], "pruned": [], "kept": 3})

        def last_run(self):
            return Ok(None)

    def test_every_task_runs_even_if_one_crashes(self):
        async def good():
            return Ok({"forged": 1})

        async def bad():
            raise RuntimeError("boom")

        report = run(scheduler.run_night(self.Service, [("bad", bad), ("good", good)]))
        self.assertTrue(report["consolidation"]["ok"])
        self.assertEqual(report["bad"], {"ok": False, "error": "crashed"})
        self.assertEqual(report["good"], {"ok": True, "forged": 1})
        self.assertEqual(scheduler.last_night()["good"]["forged"], 1)

    def test_missed_nights_are_caught_up(self):
        self.assertFalse(scheduler.overdue(None, 1_000_000.0))
        self.assertFalse(scheduler.overdue(1_000_000.0 - 3600, 1_000_000.0))
        self.assertTrue(scheduler.overdue(1_000_000.0 - 40 * 3600, 1_000_000.0))

    def test_next_run_is_always_in_the_future(self):
        self.assertGreater(scheduler.seconds_until_rem(datetime(2026, 1, 1, 12, 0)), 0)
        self.assertEqual(scheduler.seconds_until_rem(datetime(2026, 1, 1, 3, 0)), 1800.0)


@requires_native
class TrainerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.ledger = PlasticityLedger(root / "plasticity.db", ZeroTrustVault(lambda: SECRET))
        for index in range(60):
            self.ledger.add_example("light.on", f"accendi la luce {index}")
        self.installed, self.trained = [], []

    def trainer(self, gpu=True, consent="1", missing_after=False):
        def installer(missing):
            self.installed.append(missing)
            return True

        def fake_train(dataset, base, output):
            self.trained.append((dataset.exists(), base))
            return Ok({"adapter": str(output), "base_model": base})

        from server.core.plasticity import distillation
        original = distillation.missing_dependencies
        distillation.missing_dependencies = lambda: ["torch"] if missing_after and not self.installed else []
        self.addCleanup(setattr, distillation, "missing_dependencies", original)
        return AutoTrainer(self.ledger, Path(self.directory.name), installer, lambda: gpu, fake_train,
                           {"NUXIVA_CORTEX_TRAINING": consent} if consent else {})

    def test_without_consent_nothing_runs_but_the_offer_is_visible(self):
        trainer = self.trainer(consent="")
        self.assertEqual(run(trainer.cycle()).value["state"], "consent_required")
        self.assertEqual(self.trained, [])

    def test_without_a_gpu_the_state_says_so(self):
        self.assertEqual(run(self.trainer(gpu=False).cycle()).value["state"], "no_gpu")

    def test_with_consent_and_gpu_it_trains_once_a_week(self):
        trainer = self.trainer()
        first = run(trainer.cycle(now=1_000_000.0)).value
        self.assertEqual(first["state"], "trained")
        self.assertEqual(self.trained[0][0], True)
        again = run(trainer.cycle(now=1_000_000.0 + 86_400)).value
        self.assertEqual(again["state"], "recent")
        self.assertEqual(len(self.trained), 1)

    def test_missing_dependencies_are_installed_only_with_consent_and_not_every_night(self):
        trainer = self.trainer(missing_after=True)
        run(trainer.cycle(now=1_000_000.0))
        self.assertEqual(self.installed, [["torch"]])

    def test_too_few_examples_wait(self):
        empty = AutoTrainer(PlasticityLedger(Path(self.directory.name) / "other.db", ZeroTrustVault(lambda: SECRET)),
                            Path(self.directory.name), lambda m: True, lambda: True, lambda *a: Ok({}),
                            {"NUXIVA_CORTEX_TRAINING": "1"})
        self.assertEqual(run(empty.cycle()).value["state"], "waiting_for_data")


if __name__ == "__main__":
    unittest.main()
