import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.contracts import ArbiterThresholds
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository
from server.core.plasticity import distillation, rules
from server.core.plasticity.ledger import PlasticityLedger
from server.core.plasticity.scheduler import seconds_until_rem
from server.core.plasticity.service import PlasticityService
from server.tests.cortex_support import SECRET, requires_native
from server.tests.test_skill_forge import HashEmbedder

DAY = 86_400.0


class RuleTests(unittest.TestCase):
    def test_potentiation_and_depression_stay_in_bounds(self):
        weight = 0.5
        for _ in range(200):
            weight = rules.potentiate(weight)
        self.assertEqual(weight, rules.MAX_WEIGHT)
        for _ in range(200):
            weight = rules.depress(weight)
        self.assertEqual(weight, rules.MIN_WEIGHT)

    def test_decay_halves_after_one_half_life(self):
        self.assertAlmostEqual(rules.decay(0.8, rules.HALF_LIFE_DAYS), 0.4, places=6)
        self.assertEqual(rules.decay(0.8, 0), 0.8)

    def test_pruning_needs_low_weight_long_idle_and_no_protection(self):
        self.assertTrue(rules.should_prune(0.05, 120, False))
        self.assertFalse(rules.should_prune(0.05, 120, True))
        self.assertFalse(rules.should_prune(0.05, 10, False))
        self.assertFalse(rules.should_prune(0.5, 120, False))

    def test_rem_is_scheduled_for_the_next_night(self):
        self.assertAlmostEqual(seconds_until_rem(datetime(2026, 10, 22, 3, 0)), 1800.0)
        self.assertAlmostEqual(seconds_until_rem(datetime(2026, 10, 22, 4, 30)), 23 * 3600.0)


@requires_native
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        vault = ZeroTrustVault(lambda: SECRET)
        repository = EncryptedNeuronRepository(Path(self.directory.name) / "neurons.sealed", vault)
        self.hippocampus = HippocampusService(HashEmbedder(), NeuronMemory(repository), ArbiterThresholds())
        self.hippocampus.learn("light.on", ["accendi la luce", "accendi luce salotto"], 0.6)
        self.hippocampus.learn("music.play", ["suona della musica", "metti una canzone"], 0.6)
        self.ledger = PlasticityLedger(Path(self.directory.name) / "plasticity.db", vault)
        self.protected = set()
        self.service = PlasticityService(self.hippocampus, self.ledger, lambda nid: nid in self.protected)

    def weight(self, neuron_id):
        return self.hippocampus.weights().unwrap()[neuron_id]

    def test_success_strengthens_and_stores_an_example(self):
        report = self.service.feedback("light.on", "illumina la stanza", "success").unwrap()
        self.assertEqual(report["change"], "potentiated")
        self.assertGreater(self.weight("light.on"), 0.6)
        self.assertEqual(self.ledger.examples().unwrap(), [("light.on", "illumina la stanza")])

    def test_failure_weakens_and_stores_nothing(self):
        self.service.feedback("light.on", "spegni tutto", "failure")
        self.assertLess(self.weight("light.on"), 0.6)
        self.assertEqual(self.ledger.examples().unwrap(), [])

    def test_correction_moves_credit_to_the_right_neuron(self):
        report = self.service.feedback("light.on", "metti la radio", "corrected", "music.play").unwrap()
        self.assertEqual(report["corrected_to"]["neuron_id"], "music.play")
        self.assertLess(self.weight("light.on"), 0.6)
        self.assertGreater(self.weight("music.play"), 0.6)

    def test_invalid_feedback_is_rejected(self):
        self.assertEqual(self.service.feedback("light.on", "x", "wow").error.code, "cortex.plasticity.invalid")
        self.assertEqual(self.service.feedback("light.on", "x", "corrected").error.code, "cortex.plasticity.invalid")
        self.assertEqual(self.service.feedback("nope.nope", "x", "success").error.code, "cortex.neuron.unknown")

    def test_consolidation_decays_idle_neurons_once_per_night(self):
        start = 1_000_000.0
        self.ledger.touch("light.on", True, start)
        self.ledger.touch("music.play", True, start)
        night = start + 40 * DAY
        first = self.service.consolidate(night).unwrap()
        self.assertEqual(set(first["decayed"]), {"light.on", "music.play"})
        after_first = self.weight("light.on")
        self.service.consolidate(night + DAY).unwrap()
        self.assertGreater(self.weight("light.on"), after_first * 0.9)

    def test_protected_neurons_keep_their_weight_and_recent_ones_are_untouched(self):
        start = 1_000_000.0
        self.ledger.touch("light.on", True, start)
        self.ledger.touch("music.play", True, start + 39 * DAY)
        self.protected.add("light.on")
        before = self.weight("light.on"), self.weight("music.play")
        self.service.consolidate(start + 40 * DAY).unwrap()
        self.assertEqual((self.weight("light.on"), self.weight("music.play")), before)

    def test_weak_idle_neurons_are_pruned(self):
        start = 1_000_000.0
        self.hippocampus.set_weight("music.play", 0.05)
        self.ledger.touch("music.play", False, start)
        self.ledger.touch("light.on", True, start + 99 * DAY)
        report = self.service.consolidate(start + 100 * DAY).unwrap()
        self.assertEqual(report["pruned"], ["music.play"])
        self.assertNotIn("music.play", self.hippocampus.weights().unwrap())


@requires_native
class DistillationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = PlasticityLedger(Path(self.directory.name) / "p.db", ZeroTrustVault(lambda: SECRET))

    def test_too_few_examples_are_reported(self):
        self.ledger.add_example("light.on", "accendi la luce")
        outcome = distillation.build_dataset(self.ledger, Path(self.directory.name) / "d.jsonl")
        self.assertEqual(outcome.error.code, "hippocampus.distillation.no_data")

    def test_dataset_holds_only_verified_examples(self):
        for i in range(3):
            self.ledger.add_example("light.on", f"accendi la luce {i}")
        target = Path(self.directory.name) / "d.jsonl"
        self.assertEqual(distillation.build_dataset(self.ledger, target, minimum=3).unwrap(), 3)
        self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()), 3)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_training_without_dependencies_says_so(self):
        if not distillation.missing_dependencies() and distillation.gpu_available():
            self.skipTest("training stack present")
        outcome = distillation.train(Path("none.jsonl"), "some/model", Path(self.directory.name) / "out")
        self.assertEqual(outcome.error.code, "hippocampus.distillation.unavailable")


if __name__ == "__main__":
    unittest.main()
