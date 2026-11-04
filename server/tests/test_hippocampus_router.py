import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI

from server.core.core_platform.errors import fail
from server.core.core_platform.result import Ok
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router import api as hippocampus_api
from server.core.hippocampus_router import composition
from server.core.hippocampus_router.contracts import ArbiterThresholds, Verdict
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository
from server.tests.cortex_support import SECRET, asgi_get, requires_native

VECTORS = {
    "accendi la luce": [1.0, 0.0, 0.0],
    "accendi luce salotto": [0.95, 0.1, 0.0],
    "turn the light on": [0.9, 0.2, 0.05],
    "lights on please": [0.97, 0.05, 0.02],
    "suona della musica": [0.0, 1.0, 0.0],
    "quasi la luce": [0.6, 0.8, 0.0],
    "domanda aperta": [0.0, 0.0, 1.0],
}
SCHEMA = [
    {"name": "room", "entity_label": "stanza", "data_type": "enumeration", "required": True, "allowed_values": ["salotto", "cucina"]},
]


class FakeEmbedder:
    model_name = "test-double-embedder"

    def __init__(self, dimension: int = 3) -> None:
        self.dimension = dimension

    def ensure_dimension(self):
        return Ok(self.dimension)

    def state(self):
        return Ok(self.dimension)

    def embed(self, text: str):
        vector = VECTORS.get(text)
        return Ok(list(vector) + [0.0] * (self.dimension - len(vector))) if vector else fail("hippocampus.embedding.failed")


class MissingEmbedder:
    model_name = "missing"

    def ensure_dimension(self):
        return fail("hippocampus.embedding.unavailable")

    def state(self):
        return fail("hippocampus.embedding.unavailable")

    def embed(self, text: str):
        return fail("hippocampus.embedding.unavailable")


class FakeExtractor:
    def __init__(self, answer: Optional[dict] = None) -> None:
        self.answer = answer

    def extract(self, utterance: str, schema):
        return Ok(self.answer) if self.answer is not None else fail("gliner.inference_failed")


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, neuron_id: str, slots):
        self.calls.append((neuron_id, dict(slots)))
        return Ok({"done": neuron_id})


class FakeCatalog:
    def slot_schema(self, neuron_id: str):
        return SCHEMA if neuron_id == "light.on" else None


def make_service(directory: str, embedder: Any = None, secret: str = SECRET, **extras: Any) -> HippocampusService:
    vault = ZeroTrustVault(lambda: secret)
    repository = EncryptedNeuronRepository(Path(directory) / "cortex" / "neurons.sealed", vault)
    return HippocampusService(embedder or FakeEmbedder(), NeuronMemory(repository), ArbiterThresholds(), **extras)


TRAINING = ["accendi la luce", "accendi luce salotto", "turn the light on", "lights on please"]


@requires_native
class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def trained(self, **extras: Any) -> HippocampusService:
        service = make_service(self.directory.name, **extras)
        self.assertEqual(service.learn("light.on", TRAINING).unwrap(), len(TRAINING))
        return service

    def test_empty_memory_sends_everything_to_the_slow_path(self):
        outcome = make_service(self.directory.name).route("accendi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.SLOW_PATH)
        self.assertEqual(outcome.reason, "no_neurons")

    def test_known_intent_without_skills_is_demoted_and_explained(self):
        outcome = self.trained().route("accendi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.SLOW_PATH)
        self.assertEqual(outcome.degraded, "hippocampus.skills.unavailable")
        self.assertFalse(outcome.executed)
        self.assertEqual(outcome.neuron_id, "light.on")

    def test_fast_path_extracts_validates_and_executes(self):
        executor = FakeExecutor()
        service = self.trained(extractor=FakeExtractor({"room": "salotto"}), executor=executor, catalog=FakeCatalog())
        outcome = service.route("accendi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.FAST_PATH)
        self.assertTrue(outcome.executed)
        self.assertEqual(outcome.execution_result, {"done": "light.on"})
        self.assertEqual(executor.calls, [("light.on", {"room": "salotto"})])

    def test_invalid_extraction_never_reaches_the_skill(self):
        executor = FakeExecutor()
        service = self.trained(extractor=FakeExtractor({"room": "garage"}), executor=executor, catalog=FakeCatalog())
        outcome = service.route("accendi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.SLOW_PATH)
        self.assertEqual(outcome.degraded, "cortex.slots.value_not_allowed")
        self.assertEqual(executor.calls, [])

    def test_extractor_failure_is_reported_not_swallowed(self):
        service = self.trained(extractor=FakeExtractor(None), executor=FakeExecutor(), catalog=FakeCatalog())
        outcome = service.route("accendi la luce").unwrap()
        self.assertEqual(outcome.degraded, "gliner.inference_failed")

    def test_partial_match_lands_in_the_grey_zone(self):
        executor = FakeExecutor()
        service = self.trained(extractor=FakeExtractor({"room": "cucina"}), executor=executor, catalog=FakeCatalog())
        outcome = service.route("quasi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.GREY_ZONE)
        self.assertFalse(outcome.executed)
        self.assertEqual(executor.calls, [])

    def test_unrelated_request_goes_to_the_slow_path_with_reason(self):
        outcome = self.trained().route("domanda aperta").unwrap()
        self.assertEqual(outcome.verdict, Verdict.SLOW_PATH)
        self.assertEqual(outcome.reason, "low_similarity")

    def test_inhibition_blocks_a_known_false_positive(self):
        service = self.trained()
        service._memory.index(3).unwrap().add_inhibition("light.on", [1.0, 0.0, 0.0])
        outcome = service.route("accendi la luce").unwrap()
        self.assertEqual(outcome.verdict, Verdict.SLOW_PATH)
        self.assertEqual(outcome.reason, "inhibited")

    def test_hostile_input_is_rejected_before_embedding(self):
        service = self.trained()
        self.assertEqual(service.route("").error.code, "cortex.input.empty")
        self.assertEqual(service.route("a\x00b").error.code, "cortex.input.forbidden_characters")
        self.assertEqual(service.route("x" * 5000).error.code, "cortex.input.too_long")

    def test_missing_embedding_model_is_an_explicit_failure(self):
        service = make_service(self.directory.name, embedder=MissingEmbedder())
        self.assertEqual(service.route("accendi la luce").error.code, "hippocampus.embedding.unavailable")
        self.assertEqual(service.learn("light.on", TRAINING).error.code, "hippocampus.embedding.unavailable")

    def test_async_route_matches_the_sync_result(self):
        service = self.trained()
        outcome = asyncio.run(service.route_async("accendi la luce")).unwrap()
        self.assertEqual(outcome.neuron_id, "light.on")


@requires_native
class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "cortex" / "neurons.sealed"

    def test_learned_neurons_survive_a_restart_and_are_encrypted_at_rest(self):
        make_service(self.directory.name).learn("light.on", TRAINING).unwrap()
        raw = self.path.read_bytes()
        self.assertNotIn(b"light.on", raw)
        self.assertNotIn(b"dendrites", raw)
        reborn = make_service(self.directory.name)
        self.assertEqual(reborn.route("accendi la luce").unwrap().neuron_id, "light.on")
        self.assertEqual(reborn.status()["neurons"], 1)

    def test_a_wrong_key_never_overwrites_the_existing_memory(self):
        make_service(self.directory.name).learn("light.on", TRAINING).unwrap()
        before = self.path.read_bytes()
        stranger = make_service(self.directory.name, secret="another-master-secret-0123456789abcdef")
        outcome = stranger.route("accendi la luce").unwrap()
        self.assertEqual(outcome.reason, "no_neurons")
        status = stranger.status("it")
        self.assertFalse(status["storage"]["persistent"])
        self.assertEqual(status["storage"]["error"]["code"], "hippocampus.storage.undecryptable")
        stranger.learn("music.play", ["suona della musica"]).unwrap()
        self.assertEqual(self.path.read_bytes(), before)

    def test_tampered_memory_is_detected(self):
        make_service(self.directory.name).learn("light.on", TRAINING).unwrap()
        raw = bytearray(self.path.read_bytes())
        raw[-1] ^= 1
        self.path.write_bytes(bytes(raw))
        status = make_service(self.directory.name)
        status.route("accendi la luce").unwrap()
        self.assertEqual(status.status()["storage"]["error"]["code"], "hippocampus.storage.undecryptable")

    def test_changing_the_embedding_model_is_flagged_instead_of_corrupting_memory(self):
        make_service(self.directory.name).learn("light.on", TRAINING).unwrap()
        before = self.path.read_bytes()
        wider = make_service(self.directory.name, embedder=FakeEmbedder(dimension=4))
        wider.route("accendi la luce").unwrap()
        self.assertEqual(wider.status()["storage"]["error"]["code"], "cortex.vector.dimension_mismatch")
        wider.learn("music.play", ["suona della musica"]).unwrap()
        self.assertEqual(self.path.read_bytes(), before)


@requires_native
class StatusTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def test_telemetry_counts_decisions_without_storing_user_text(self):
        service = make_service(self.directory.name)
        service.learn("light.on", TRAINING).unwrap()
        service.route("accendi la luce").unwrap()
        service.route("domanda aperta").unwrap()
        telemetry = service.status()["telemetry"]
        self.assertEqual(telemetry["total"], 2)
        self.assertEqual(telemetry["verdicts"], {"slow_path": 2})
        self.assertEqual(len(telemetry["recent"]), 2)
        self.assertNotIn("accendi", str(telemetry))
        self.assertGreaterEqual(telemetry["latency_ms"]["maximum"], telemetry["latency_ms"]["average"])

    def test_status_describes_every_dependency_without_loading_models(self):
        status = make_service(self.directory.name, embedder=MissingEmbedder()).status("en")
        self.assertTrue(status["native"]["available"])
        self.assertFalse(status["embedding"]["loaded"])
        self.assertEqual(status["embedding"]["error"]["code"], "hippocampus.embedding.unavailable")
        self.assertIn("embedding", status["embedding"]["error"]["message"].lower())
        self.assertEqual(status["execution"], {"extractor": False, "executor": False, "catalog": False})
        self.assertEqual(status["thresholds"]["fast_similarity"], 0.85)

    def test_status_endpoint_serves_the_service_snapshot(self):
        service = make_service(self.directory.name)
        previous = composition._service
        composition._service = service
        self.addCleanup(setattr, composition, "_service", previous)
        app = FastAPI()
        app.include_router(hippocampus_api.router)
        status, body = asgi_get(app, "/api/v1/cognition/hippocampus/status")
        self.assertEqual(status, 200)
        self.assertEqual(body["embedding"]["model"], "test-double-embedder")


if __name__ == "__main__":
    unittest.main()
