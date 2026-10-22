import asyncio
import hashlib
import math
import tempfile
import unittest
from pathlib import Path

from server.core.core_platform.errors import fail
from server.core.core_platform.result import Ok
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.contracts import ArbiterThresholds, Verdict
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository
from server.core.orchestrator.hippocampus_gate import try_fast_path
from server.core.skill_forge.ast_scanner import scan_source
from server.core.skill_forge.forge import SkillForge, SkillRuntime
from server.core.skill_forge.sandbox import run_isolated
from server.core.skill_forge.store import SkillStore
from server.core.skill_forge.synthetic import expand
from server.tests.cortex_support import SECRET, requires_native

GOOD = "import math\ndef run(slots):\n    return {'speech': 'luce ' + slots['room'] + ' ' + str(int(math.floor(2.5)))}\n"
SCHEMA = [{"name": "room", "entity_label": "stanza", "data_type": "enumeration", "required": True,
           "allowed_values": ["salotto", "cucina"]}]


class HashEmbedder:
    model_name = "test-hash-embedder"

    def ensure_dimension(self):
        return Ok(64)

    def state(self):
        return Ok(64)

    def embed(self, text: str):
        vector = [0.0] * 64
        padded = f"  {text.lower()}  "
        for i in range(len(padded) - 2):
            digest = hashlib.sha256(padded[i:i + 3].encode()).digest()
            vector[digest[0] % 64] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return Ok([v / norm for v in vector])


class MissingEmbedder(HashEmbedder):
    def ensure_dimension(self):
        return fail("hippocampus.embedding.unavailable")

    def embed(self, text: str):
        return fail("hippocampus.embedding.unavailable")


class FixedExtractor:
    def extract(self, utterance, schema):
        return Ok({"room": "salotto"})


def manifest(neuron_id="light.on"):
    return {"neuron_id": neuron_id, "title": "Accendi luce", "slot_schema": SCHEMA,
            "utterances": ["accendi la luce {room}", "accendi luce {room}"],
            "cases": [{"slots": {"room": "salotto"}, "expect_speech": "luce salotto 2"}]}


class ScannerTests(unittest.TestCase):
    def codes(self, source):
        result = scan_source(source)
        return None if result.is_ok else result.error.code

    def test_valid_skill_passes(self):
        self.assertIsNone(self.codes(GOOD))

    def test_forbidden_constructs_are_rejected(self):
        cases = {
            "import os\ndef run(slots):\n    return {}": "cortex.forge.forbidden_import",
            "from subprocess import run\ndef run(slots):\n    return {}": "cortex.forge.forbidden_import",
            "def run(slots):\n    return eval('1')": "cortex.forge.forbidden_call",
            "def run(slots):\n    return getattr(slots, 'x')": "cortex.forge.forbidden_call",
            "def run(slots):\n    return ().__class__": "cortex.forge.forbidden_syntax",
            "def run(slots):\n    return '{0.x}'.format(slots)": "cortex.forge.forbidden_syntax",
            "class A:\n    pass\ndef run(slots):\n    return {}": "cortex.forge.forbidden_syntax",
            "def run(slots):\n    return {": "cortex.forge.syntax",
            "def other(slots):\n    return {}": "cortex.forge.missing_entry",
            "def run(a, b):\n    return {}": "cortex.forge.missing_entry",
        }
        for source, code in cases.items():
            self.assertEqual(self.codes(source), code, source)

    def test_oversized_source_is_rejected(self):
        self.assertEqual(self.codes("x = 1\n" * 20_000), "cortex.forge.source_too_large")


class SandboxTests(unittest.TestCase):
    def test_runs_a_valid_skill(self):
        self.assertEqual(run_isolated(GOOD, {"room": "cucina"}).unwrap(), {"speech": "luce cucina 2"})

    def test_infinite_loop_is_stopped(self):
        outcome = run_isolated("def run(slots):\n    while True:\n        pass\n", {})
        self.assertEqual(outcome.error.code, "cortex.forge.timeout")

    def test_invalid_output_is_rejected(self):
        self.assertEqual(run_isolated("def run(slots):\n    return [1]\n", {}).error.code, "cortex.forge.output_invalid")
        self.assertEqual(run_isolated("def run(slots):\n    return {'speech': 'x' * 5000}\n", {}).error.code,
                         "cortex.forge.output_invalid")

    def test_runtime_import_and_open_are_blocked(self):
        self.assertEqual(run_isolated("def run(slots):\n    import os\n    return {'speech': 'x'}\n", {}).error.code,
                         "cortex.forge.runtime_failed")
        self.assertEqual(run_isolated("def run(slots):\n    return {'speech': open('/etc/passwd').read()}\n", {}).error.code,
                         "cortex.forge.runtime_failed")


class SyntheticTests(unittest.TestCase):
    def test_placeholders_expand_and_variants_are_bounded(self):
        utterances, synthetic = expand(["accendi la luce {room}"], SCHEMA)
        self.assertIn("accendi la luce salotto", utterances)
        self.assertIn("accendi la luce cucina", utterances)
        self.assertGreater(synthetic, 0)
        self.assertLessEqual(len(utterances), 128)

    def test_unfillable_placeholder_is_dropped_not_invented(self):
        utterances, synthetic = expand(["accendi {thing}"], SCHEMA)
        self.assertEqual((utterances, synthetic), ([], 0))


@requires_native
class ForgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.vault = ZeroTrustVault(lambda: SECRET)
        self.store = SkillStore(Path(self.directory.name) / "skills.sealed", self.vault)
        self.runtime = SkillRuntime(self.store)

    def service(self, embedder=None):
        repository = EncryptedNeuronRepository(Path(self.directory.name) / "neurons.sealed", self.vault)
        return HippocampusService(embedder or HashEmbedder(), NeuronMemory(repository), ArbiterThresholds(),
                                  extractor=FixedExtractor(), executor=self.runtime, catalog=self.runtime)

    def test_forged_skill_is_signed_listed_and_executable(self):
        service = self.service()
        forged = SkillForge(service, self.store).forge(manifest(), GOOD)
        self.assertTrue(forged.is_ok, forged)
        self.assertGreater(forged.value["synthetic"], 0)
        self.assertEqual(self.store.listing().unwrap()[0]["neuron_id"], "light.on")
        self.assertEqual(self.runtime.execute("light.on", {"room": "salotto"}).unwrap(), {"speech": "luce salotto 2"})

    def test_failing_example_blocks_the_skill(self):
        data = manifest()
        data["cases"][0]["expect_speech"] = "altro"
        outcome = SkillForge(self.service(), self.store).forge(data, GOOD)
        self.assertEqual(outcome.error.code, "cortex.forge.output_invalid")
        self.assertEqual(self.store.listing().unwrap(), [])

    def test_unsafe_code_never_reaches_the_store(self):
        outcome = SkillForge(self.service(), self.store).forge(manifest(), "import os\ndef run(slots):\n    return {}\n")
        self.assertEqual(outcome.error.code, "cortex.forge.forbidden_import")
        self.assertEqual(self.store.listing().unwrap(), [])

    def test_learning_failure_rolls_the_skill_back(self):
        outcome = SkillForge(self.service(MissingEmbedder()), self.store).forge(manifest(), GOOD)
        self.assertEqual(outcome.error.code, "hippocampus.embedding.unavailable")
        self.assertEqual(self.store.listing().unwrap(), [])

    def test_tampered_registry_is_not_executed(self):
        SkillForge(self.service(), self.store).forge(manifest(), GOOD)
        record = self.store._records["light.on"]
        other = SkillStore(Path(self.directory.name) / "other.sealed", self.vault)
        other.put("light.on", "x", {"neuron_id": "light.on", "source": "def run(slots):\n    return {'speech': 'hack'}\n",
                                    "slot_schema": []}, "manual", 0)
        record["payload"] = other._records["light.on"]["payload"]
        self.assertEqual(self.runtime.execute("light.on", {"room": "salotto"}).error.code, "cortex.forge.untrusted")
        self.assertIsNone(self.runtime.slot_schema("light.on"))

    def test_fast_path_end_to_end_through_the_gate(self):
        service = self.service()
        SkillForge(service, self.store).forge(manifest(), GOOD)
        response, summary = asyncio.run(try_fast_path("accendi la luce salotto", "it", lambda: service))
        self.assertIsNotNone(response, summary)
        self.assertEqual(response.speech_output, "luce salotto 2")
        self.assertEqual(response.agent_id, "hippocampus_fast_path")

    def test_unknown_request_goes_to_the_slow_path(self):
        service = self.service()
        SkillForge(service, self.store).forge(manifest(), GOOD)
        response, summary = asyncio.run(try_fast_path("racconta una barzelletta sui gatti", "it", lambda: service))
        self.assertIsNone(response)
        self.assertNotIn("fast_path", summary.split(" · ")[0].replace("slow path", ""))

    def test_gate_survives_a_broken_service(self):
        def broken():
            raise RuntimeError("boom")

        response, summary = asyncio.run(try_fast_path("accendi la luce", "it", broken))
        self.assertIsNone(response)
        self.assertIn("RuntimeError", summary)

    def test_retiring_removes_the_neuron(self):
        service = self.service()
        forge = SkillForge(service, self.store)
        forge.forge(manifest(), GOOD)
        self.assertTrue(forge.retire("light.on").unwrap())
        self.assertEqual(service.route("accendi la luce salotto").unwrap().verdict, Verdict.SLOW_PATH)


if __name__ == "__main__":
    unittest.main()
