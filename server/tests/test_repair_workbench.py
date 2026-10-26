import asyncio
import base64
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from server.core.agent_registry.forge import agent_forge
from server.cmd.route_scanner import FeatureRouteScanner
from server.features.project_workspace.inter_agent_dialogue import post_inter_agent_message
from server.features.project_workspace.manager import project_manager
from server.features.repair_workbench import workbench_controller as controller
from server.features.repair_workbench.circuit_schemas import CircuitSpec
from server.features.repair_workbench.collaboration_service import WorkbenchCollaboration
from server.features.repair_workbench.errors import SessionAccessException, VisionUnavailableException
from server.features.repair_workbench.fallback_engine import PythonComponentTracker, PythonStabilityGate
from server.features.repair_workbench.launch_queue import WorkbenchLaunchQueue
from server.features.repair_workbench.mna_solver import solve_ac, solve_dc
from server.features.repair_workbench.native_bridge import WorkbenchEngine
from server.features.repair_workbench.ollama_vision import OllamaVisionAnalyzer
from server.features.repair_workbench.session_models import VisionObservation
from server.features.repair_workbench.session_requests import AnalyzeFrameRequest
from server.features.repair_workbench.session_store import EncryptedSessionStore
from server.features.repair_workbench.workbench_service import WorkbenchService
from server.features.repair_workbench.supervisor_vision import ConfiguredVisionAnalyzer
from server.features.repair_workbench.team_service import WorkbenchTeamService
from server.shared.errors.global_handler import register_global_error_handlers

FRAME = base64.b64encode(b"\xff\xd8\xff" + b"sample-frame").decode()


def divider():
    return CircuitSpec.model_validate({
        "components": [
            {"ref": "V1", "category": "voltage_source", "value": "10V"},
            {"ref": "R1", "category": "resistor", "value": "1k"},
            {"ref": "R2", "category": "resistor", "value": "1k"},
        ],
        "nets": [
            {"name": "VCC", "connections": [{"ref": "V1", "pin": "1"}, {"ref": "R1", "pin": "1"}]},
            {"name": "OUT", "connections": [{"ref": "R1", "pin": "2"}, {"ref": "R2", "pin": "1"}]},
            {"name": "GND", "connections": [{"ref": "V1", "pin": "2"}, {"ref": "R2", "pin": "2"}]},
        ],
    })


def observation():
    circuit = divider()
    return VisionObservation.model_validate({
        "title": "Banco di prova", "summary": "Partitore resistivo",
        "components": [
            {"ref": c.ref, "label": c.ref, "value": c.value, "category": c.category,
             "bbox": [0.1 + i * 0.2, 0.2, 0.25 + i * 0.2, 0.4]}
            for i, c in enumerate(circuit.components)
        ],
        "connections": [{"net": n.name, "pins": n.connections} for n in circuit.nets],
        "advice": ["Verificare il valore delle resistenze"],
    })


class TestRepairWorkbenchAPI(unittest.TestCase):
    def test_project_archive_resume_and_close_preserve_history(self):
        self.assertEqual(self.analyze().status_code, 200)
        prefix = "/api/v1/repair-workbench"
        listing = self.client.get(prefix + "/projects/archive").json()["projects"]
        self.assertEqual(listing[0]["project_id"], self.project.project_id)
        restored = self.client.post(prefix + f"/projects/{self.project.project_id}/resume")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["session"]["circuit"]["components"][1]["ref"], "R1")
        closed = self.client.post(prefix + f"/projects/{self.project.project_id}/close")
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(self.client.get(prefix + "/projects/archive").json()["projects"], [])
        self.assertEqual(len(self.client.get(prefix + "/projects/archive?include_closed=true").json()["projects"]), 1)
        self.assertEqual(self.client.post(prefix + f"/projects/{self.project.project_id}/resume").status_code, 404)

    def test_registered_issue_is_resolved_and_retained_by_team_api(self):
        created = self.client.post(self.url + "/issues", json={"title": "Il pulsante non risponde", "severity": "high"})
        self.assertEqual(created.status_code, 200)
        issue_id = created.json()["team"]["issues"][0]["id"]
        resolved = self.client.post(self.url + f"/issues/{issue_id}/status", json={"status": "resolved", "resolution": "Contatto ripristinato"})
        self.assertEqual(resolved.status_code, 200)
        issue = self.client.get(self.url + "/team").json()["team"]["issues"][0]
        self.assertEqual((issue["status"], issue["resolution"]), ("resolved", "Contatto ripristinato"))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self._patch(project_manager, "_store_dir", str(self.root / "projects"))
        self._patch(project_manager, "_notify_widget", lambda *_: None)
        self._patch(agent_forge, "_custom_agents_dir", str(self.root / "agents"))
        self._patch(agent_forge, "_agents", dict(agent_forge._agents))
        (self.root / "agents").mkdir()
        self.clock = [100.0]
        self.analyzer = SimpleNamespace(analyze=AsyncMock(return_value=observation()))
        self.store = EncryptedSessionStore(str(self.root / "sessions"))
        self.native_patch = patch.object(WorkbenchEngine, "_load_native", return_value=None)
        self.native_patch.start()
        self.addCleanup(self.native_patch.stop)
        self.service = WorkbenchService(self.store, self.analyzer, clock=lambda: self.clock[0])
        self._patch(controller, "workbench_service", self.service)
        self._patch(controller, "workbench_collaboration", WorkbenchCollaboration(self.service))
        self._patch(controller, "workbench_team", WorkbenchTeamService(
            self.service, controller.workbench_collaboration, executors={}))
        self._patch(controller, "workbench_launch_queue", WorkbenchLaunchQueue())
        self.project = project_manager.create_project("user_primary", "Banco", "riparazione scheda elettronica amplificatore")
        app = FastAPI()
        app.include_router(controller.workbench_router, prefix="/api/v1")
        register_global_error_handlers(app)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        response = self.client.post("/api/v1/repair-workbench/sessions", json={
            "project_id": self.project.project_id, "camera_name": "Telecamera Banco Riparazioni",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.session = response.json()["session"]
        self.url = "/api/v1/repair-workbench/sessions/" + self.session["session_id"]

    def _patch(self, target, name, value):
        patcher = patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def analyze(self, **extra):
        return self.client.post(self.url + "/analyze-frame", json={"frame_base64": FRAME, **extra})

    def test_frame_to_dossier_popups_schematic_and_voltages(self):
        response = self.analyze()
        self.assertEqual(response.status_code, 200, response.text)
        session = response.json()["session"]
        self.assertTrue(response.json()["analyzed"])
        self.assertEqual(session["dossier"]["component_count"], 3)
        self.assertEqual(len(session["popups"]), 3)
        self.assertEqual(len(session["circuit"]["nets"]), 3)
        self.assertAlmostEqual(session["expected_voltages"]["OUT"], 5.0)
        self.assertNotIn("owner_id", session)

    def test_encrypted_reload_and_owner_isolation(self):
        self.analyze()
        session_id = self.session["session_id"]
        encrypted = (self.root / "sessions" / "user_primary" / f"{session_id}.enc").read_bytes()
        self.assertNotIn(b"Partitore", encrypted)
        self.service._cache.clear()
        loaded = self.client.get(self.url)
        self.assertEqual(loaded.json()["session"]["dossier"]["component_count"], 3)
        self.assertEqual(self.client.get(self.url, params={"user_id": "another_owner"}).status_code, 404)

    def test_tampered_ciphertext_is_rejected(self):
        path = self.root / "sessions" / "user_primary" / f"{self.session['session_id']}.enc"
        path.write_bytes(b"invalid-token")
        self.service._cache.clear()
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_mismatched_encrypted_identity_is_rejected(self):
        session = self.service.get("user_primary", self.session["session_id"])
        other = session.model_copy(update={"session_id": "other"})
        self.store.save(other)
        source = self.root / "sessions" / "user_primary" / "other.enc"
        target = source.with_name(session.session_id + ".enc")
        target.write_bytes(source.read_bytes())
        with self.assertRaises(SessionAccessException):
            self.store.load("user_primary", session.session_id)

    def test_store_rejects_directory_traversal(self):
        for owner in ("..", ".", "../outside", "a/b", "a\\b"):
            with self.subTest(owner=owner), self.assertRaises(SessionAccessException):
                self.store.load(owner, "session")
        self.assertEqual(self.client.get(self.url, params={"user_id": ".."}).status_code, 422)

    def test_unknown_project_and_track(self):
        response = self.client.post("/api/v1/repair-workbench/sessions", json={"project_id": "missing"})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(self.url + "/teach-component", json={"track_id": 99, "label": "R1"})
        self.assertEqual(response.status_code, 404)

    def test_frame_validation(self):
        for frame in ("!" * 20, base64.b64encode(b"plain text file").decode()):
            with self.subTest(frame=frame):
                response = self.client.post(self.url + "/analyze-frame", json={"frame_base64": frame})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.analyze(grid=[256]).status_code, 422)
        self.assertEqual(self.analyze(grid=[0] * 4097).status_code, 422)
        self.analyzer.analyze.assert_not_awaited()

    def test_analysis_is_throttled_and_skipped_during_motion(self):
        self.assertTrue(self.analyze(grid=[0] * 64).json()["analyzed"])
        self.assertFalse(self.analyze(grid=[0] * 64).json()["analyzed"])
        self.clock[0] += 4
        response = self.analyze(grid=[255] * 64).json()
        self.assertFalse(response["analyzed"])
        self.assertEqual(response["session"]["scene_state"], "operator_working")
        self.analyzer.analyze.assert_awaited_once()

    def test_vision_unavailable_is_explicit_and_retryable(self):
        self.analyzer.analyze.side_effect = VisionUnavailableException("offline")
        self.assertEqual(self.analyze().status_code, 503)
        self.analyzer.analyze.side_effect = None
        self.assertEqual(self.analyze().status_code, 200)

    def test_concurrent_frames_do_not_duplicate_inference(self):
        async def run():
            entered, release = asyncio.Event(), asyncio.Event()
            async def slow(*_):
                entered.set()
                await release.wait()
                return observation()
            self.analyzer.analyze.side_effect = slow
            request = AnalyzeFrameRequest(frame_base64=FRAME)
            first = asyncio.create_task(self.service.analyze("user_primary", self.session["session_id"], request))
            await entered.wait()
            _, analyzed = await self.service.analyze("user_primary", self.session["session_id"], request)
            self.assertFalse(analyzed)
            release.set()
            self.assertTrue((await first)[1])
        asyncio.run(run())
        self.analyzer.analyze.assert_awaited_once()

    def test_repeated_teaching_survives_next_observation_and_reload(self):
        self.analyze()
        session = self.client.get(self.url).json()["session"]
        track = next(p["track_id"] for p in session["popups"] if p["key"] == "R1")
        for label in ("Resistenza", "Ingresso"):
            response = self.client.post(self.url + "/teach-component", json={
                "track_id": track, "label": label, "value": "2k",
            })
            self.assertEqual(response.status_code, 200)
        self.service._cache.clear()
        self.clock[0] += 4
        response = self.analyze().json()["session"]
        popup = next(p for p in response["popups"] if p["key"] == "Ingresso")
        self.assertTrue(popup["taught"])
        self.assertEqual(popup["value"], "2k")
        self.assertEqual(next(c for c in response["circuit"]["components"] if c["ref"] == "R1")["value"], "2k")

    def test_chat_persists_reply_and_rejects_unassigned_agent(self):
        response = SimpleNamespace(is_synthetic=False, content="Controllare R1")
        with patch("server.features.repair_workbench.collaboration_service.llm_gateway.generate_completion",
                   new=AsyncMock(return_value=response)) as completion:
            reply = self.client.post(self.url + "/chat", json={"message": "Da dove parto?"})
            self.assertEqual(reply.status_code, 200, reply.text)
            self.assertEqual(reply.json()["reply"]["text"], response.content)
            denied = self.client.post(self.url + "/chat", json={"message": "Test", "agent_id": "unknown"})
            self.assertEqual(denied.status_code, 404)
            completion.assert_awaited_once()
        self.assertEqual(len(self.client.get(self.url).json()["session"]["notes"]), 1)
        self.assertEqual(len(project_manager.get_by_id("user_primary", self.project.project_id).war_room_feed), 3)

    def test_synthetic_chat_is_not_presented_as_expert_advice(self):
        with patch("server.features.repair_workbench.collaboration_service.llm_gateway.generate_completion",
                   new=AsyncMock(return_value=SimpleNamespace(is_synthetic=True, content="fallback"))):
            response = self.client.post(self.url + "/chat", json={"message": "Test"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.client.get(self.url).json()["session"]["notes"], [])

    def test_escalation_forges_once_and_reuses_catalog_agent(self):
        payload = {"requester_agent_id": "electronics_repair_engineer", "specialty": "power diagnosis",
                   "justification": "Analizzare lo stadio di alimentazione"}
        first = self.client.post(self.url + "/escalate", json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["result"]["forged"])
        self.assertFalse(self.client.post(self.url + "/escalate", json=payload).json()["result"]["forged"])
        payload["specialty"] = "embedded_firmware_coder"
        result = self.client.post(self.url + "/escalate", json=payload).json()["result"]
        self.assertEqual(result["specialist_id"], "embedded_firmware_coder")
        self.assertFalse(result["forged"])

    def test_escalation_rejects_outsider_before_forging(self):
        response = self.client.post(self.url + "/escalate", json={
            "requester_agent_id": "outsider", "specialty": "unregistered specialist", "justification": "Test",
        })
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(agent_forge.get_agent("expert_unregistered_specialist"))

    def test_inter_agent_dialogue_checks_team_membership(self):
        message = post_inter_agent_message(self.project, "electronics_repair_engineer", "pcb_schematic_architect", "Verifica collegamenti")
        self.assertTrue(message.metadata["inter_agent"])
        self.assertIsNone(post_inter_agent_message(self.project, "outsider", "pcb_schematic_architect", "Test"))

    def test_repair_command_assigns_team_and_queues_owner_launch(self):
        queue = WorkbenchLaunchQueue()
        with patch("server.features.project_workspace.manager.workbench_launch_queue", queue):
            result = project_manager.process_query("Apri un nuovo progetto per aggiustare una scheda elettronica di un amplificatore", "user_primary")
        self.assertIn("PROJECT_START", result)
        requests = queue.pending("user_primary", 0)
        self.assertEqual(len(requests), 1)
        project = project_manager.get_by_id("user_primary", requests[0].project_id)
        self.assertIn("audio_acoustics_specialist", project.assigned_agents)
        self.assertEqual(queue.pending("other", 0), [])


class TestWorkbenchNumerics(unittest.TestCase):
    def test_configured_vision_uses_supervisor_and_reports_model(self):
        import httpx
        async def run():
            response = httpx.Response(200, json={"summary": "Scheda", "model_used": "configured-vision"},
                                      request=httpx.Request("POST", "http://supervisor/analyze"))
            with patch.dict("os.environ", {"NUXIVA_VISION_MODEL": ""}), \
                 patch("server.features.repair_workbench.supervisor_vision.bridge._post", new=AsyncMock(return_value=response)) as post:
                result = await ConfiguredVisionAnalyzer().analyze(b"frame", "it", ["R1"])
            self.assertEqual(result.model_used, "configured-vision")
            self.assertEqual(post.call_args.args[0], "/api/internal/repair-workbench/analyze")
        asyncio.run(run())

    def test_production_scanner_discovers_workbench_router(self):
        scanner = FeatureRouteScanner()
        directory = str(Path(scanner.features_dir) / "repair_workbench")
        with patch("server.cmd.route_scanner.os.walk", return_value=[(directory, [], ["workbench_controller.py"])]):
            routers = scanner.scan_routers()
        self.assertIn(controller.workbench_router, routers)

    def test_dc_divider_and_ac_gain(self):
        self.assertAlmostEqual(solve_dc(divider())["OUT"], 5.0)
        self.assertAlmostEqual(solve_ac(divider(), [100.0], "OUT")[0], 20 * math.log10(5.0))

    def test_current_source_polarity(self):
        circuit = divider()
        circuit.components[0].category = "current_source"
        circuit.components[0].value = "1mA"
        self.assertAlmostEqual(solve_dc(circuit)["VCC"], -2.0)

    def test_floating_and_conflicting_networks_have_no_voltages(self):
        circuit = divider()
        circuit.nets[-1].name = "FLOAT"
        self.assertEqual(solve_dc(circuit), {})
        circuit = divider()
        source = circuit.components[0].model_copy(update={"ref": "V2", "value": "20V"})
        circuit.components.append(source)
        from server.features.repair_workbench.circuit_schemas import PinRef
        circuit.nets[0].connections.append(PinRef(ref="V2", pin="1"))
        circuit.nets[-1].connections.append(PinRef(ref="V2", pin="2"))
        self.assertEqual(solve_dc(circuit), {})

    def test_unsupported_devices_and_invalid_frequencies(self):
        circuit = divider()
        circuit.components[1].category = "transistor"
        self.assertEqual(solve_dc(circuit), {})
        self.assertEqual(solve_ac(divider(), [-1, math.inf, math.nan], "OUT"), [None] * 3)

    def test_pin_assigned_to_multiple_nets_has_no_voltage_prediction(self):
        circuit = divider()
        circuit.nets[-1].connections.append(circuit.nets[0].connections[0])
        self.assertEqual(solve_dc(circuit), {})

    def test_stability_and_track_identity(self):
        gate = PythonStabilityGate()
        self.assertEqual(gate.observe([0] * 64), "warmup")
        for _ in range(3):
            state = gate.observe([0] * 64)
        self.assertEqual(state, "stable_board")
        self.assertEqual(gate.observe([255] * 64), "operator_working")
        tracker = PythonComponentTracker()
        first = tracker.update([{"label": "R1", "bbox": [0.1, 0.1, 0.3, 0.3]}])[0]
        second = tracker.update([{"label": "R1", "bbox": [0.11, 0.1, 0.31, 0.3]}])[0]
        self.assertEqual(first["track_id"], second["track_id"])
        self.assertLess(second["bbox"][0], 0.11)

    def test_invalid_boxes_are_rejected(self):
        with self.assertRaises(ValidationError):
            VisionObservation.model_validate({"components": [{"label": "R1", "bbox": [0, 0, math.nan, 1]}]})

    def test_unreadable_reference_does_not_discard_other_components(self):
        result = VisionObservation.model_validate({"components": [
            {"ref": "", "label": "Condensatore", "bbox": [0.1, 0.2, 0.3, 0.4]},
            {"ref": "R1", "label": "Resistenza", "bbox": [0.4, 0.2, 0.5, 0.4]},
        ]})
        self.assertIsNone(result.components[0].ref)
        self.assertEqual(result.components[1].ref, "R1")

    def test_malformed_vision_envelope_is_unavailable(self):
        async def run():
            fake = SimpleNamespace(raise_for_status=lambda: None, json=lambda: [])
            client = AsyncMock()
            client.post.return_value = fake
            with patch("server.features.repair_workbench.ollama_vision.httpx.AsyncClient") as factory:
                factory.return_value.__aenter__.return_value = client
                with self.assertRaises(VisionUnavailableException):
                    await OllamaVisionAnalyzer().analyze(b"frame", "it", [])
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
