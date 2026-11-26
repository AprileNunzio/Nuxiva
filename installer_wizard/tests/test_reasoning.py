import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import native_core
from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.reasoning import act, api, contracts, models, pipeline, shadow, sources, state, traces

GOAL = {"intent": "get_weather", "language": "it", "effects": ["read"],
        "entities": [{"role": "city", "ty": "text", "value": "Roma", "source": "user"}], "confidence_bps": 9300}
PLAN = {"steps": [{"id": "forecast", "capability": "weather", "args": {"city": {"from": "entity", "role": "city"}}}]}
DOC = {"schema": 1, "capabilities": [
    {"id": "weather", "version": 1, "origin": "local", "summary": "Meteo di una città", "inputs": [{"name": "city", "ty": "text", "required": True}],
     "output": "text", "effects": ["read"], "reversible": True, "min_role": "guest", "nodes": ["server"]},
    {"id": "chat.answer", "version": 1, "origin": "local", "summary": "Risposta", "inputs": [{"name": "question", "ty": "text", "required": True}],
     "output": "text", "effects": ["read"], "reversible": True, "min_role": "guest", "nodes": ["server"]}]}
NATIVE = native_core.symbol("RustReasonEngine") is not None


def schema_of(name):
    return {"properties": {"city": {"type": "string"}, "days": {"type": "integer"}, "Bad Key": {"type": "string"}}, "required": ["city"]}


class ContractTests(unittest.TestCase):
    def test_tools_connectors_and_chat_become_contracts(self):
        tools = [{"name": "weather", "description": "Meteo " * 80, "confirm": False, "full_only": False, "agent": "weather"},
                 {"name": "send_email", "description": "Invia", "confirm": True, "full_only": False, "agent": ""},
                 {"name": "Bad-Name", "description": "x", "confirm": False},
                 {"name": "lamp", "description": "Luce", "confirm": False, "effects": ["physical"]}]
        doc = contracts.document(tools, schema_of, {"music": "Musica"}, "Conversazione")
        by_id = {c["id"]: c for c in doc["capabilities"]}
        self.assertEqual(set(by_id), {"weather", "send_email", "lamp", "connector.music", "chat.answer"})
        self.assertLessEqual(len(by_id["weather"]["summary"].encode()), 240)
        self.assertEqual([p["name"] for p in by_id["weather"]["inputs"]], ["city", "days"])
        self.assertEqual(by_id["weather"]["inputs"][1]["ty"], "number")
        self.assertEqual(by_id["send_email"]["effects"], ["send_external", "write"])
        self.assertFalse(by_id["send_email"]["reversible"])
        self.assertEqual(by_id["send_email"]["min_role"], "family")
        self.assertEqual(by_id["lamp"]["effects"], ["physical"])
        self.assertNotIn("inferred", by_id["lamp"]["tags"])
        self.assertEqual(contracts.inferred(doc), 3)

    def test_legacy_mapping(self):
        connectors = {"music": "agenti.music.commands"}
        self.assertEqual(shadow.legacy_capabilities({"intent": "agent"}, ["weather"], connectors), ["weather"])
        self.assertEqual(shadow.legacy_capabilities({"intent": "music"}, [], connectors), ["connector.music"])
        self.assertEqual(shadow.legacy_capabilities({"intent": "conversation"}, [], connectors), ["chat.answer"])
        self.assertIsNone(shadow.legacy_capabilities({"intent": "scene"}, [], connectors))

    def test_roles_never_escalate(self):
        self.assertEqual(pipeline.role_of("anonymous"), "guest")
        self.assertEqual(pipeline.role_of("system"), "owner")


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class EngineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        patches = [mock.patch.object(state, "ROOT", root), mock.patch.object(state, "KEY", root / "reasoning.key"),
                   mock.patch.object(state, "JOURNAL", root / "journal"), mock.patch.object(state, "LEDGER", root / "ledger.json"),
                   mock.patch.object(state, "SWITCH", root / "switch.json"), mock.patch.object(state, "CONFIG", root / "config.json"),
                   mock.patch.object(sources, "build", lambda: DOC), mock.patch.object(models, "understand", self.understand),
                   mock.patch.object(models, "plan", self.plan)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        state.reload()
        sources._last.update({"at": 0.0, "fingerprint": ""})
        self.addCleanup(state.reload)
        self.addCleanup(self.temp.cleanup)
        self.plans = [json.dumps(PLAN)]
        self.goal = dict(GOAL)

    async def understand(self, request, privacy=""):
        return json.dumps(self.goal), 10

    async def plan(self, request, privacy=""):
        self.assertNotIn("Roma", request["user"])
        return self.plans.pop(0), 20

    async def test_think_accepts_and_caches_plan(self):
        thought = await pipeline.think("che tempo fa a Roma", "guest")
        self.assertTrue(thought.executable, thought.code)
        self.assertEqual(thought.capabilities, ["weather"])
        again = await pipeline.think("che tempo fa a Roma", "guest")
        self.assertTrue(again.checked["cached"])
        self.assertEqual(again.tokens, 10)

    async def test_think_corrects_once_then_rejects(self):
        bad = json.dumps({"steps": [{"id": "x", "capability": "unknown"}]})
        self.plans = [bad, bad]
        thought = await pipeline.think("che tempo fa a Roma", "guest")
        self.assertFalse(thought.valid)
        self.assertEqual(thought.corrections, 1)
        self.assertTrue(thought.code.startswith("plan.unlisted_capability"))

    async def test_low_confidence_stops_before_planning(self):
        self.goal["confidence_bps"] = 1000
        thought = await pipeline.think("che tempo fa a Roma", "guest")
        self.assertEqual(thought.code, "reason.goal.low_confidence")
        self.assertEqual(thought.stage, "understand")

    async def test_shadow_records_agreement_and_persists(self):
        state.engine()
        await shadow.observe("che tempo fa a Roma", "guest", {"intent": "agent", "reply": "ok"}, ["weather"], {})
        status = json.loads(state.engine().status(state.now_ms()))
        self.assertEqual(status["gate"]["samples"], 1)
        self.assertEqual(status["gate"]["agreement_bps"], 10000)
        self.assertTrue(state.LEDGER.exists())
        self.assertEqual(traces.recent(1)[0]["agreed"], True)

    async def test_active_mode_requires_gate_and_executes_once(self):
        with self.assertRaises(ValueError):
            state.engine().set_mode("active", False, state.now_ms())
        state.engine().set_mode("active", True, state.now_ms())
        self.assertTrue(act.active())
        calls = []

        async def dispatch(self_, capability, args):
            calls.append((capability, args))
            return json.dumps({"ok": True, "output": f"Sole a {args['city']}"})

        with mock.patch("agenti.reasoning.invoker.Invoker.dispatch", dispatch):
            first = await act.attempt("che tempo fa a Roma", "guest", "it")
            self.plans = [json.dumps(PLAN)]
            second = await act.attempt("che tempo fa a Roma", "guest", "it")
        self.assertEqual(first["reply"], "Sole a Roma")
        self.assertEqual(second["reply"], "Sole a Roma")
        self.assertEqual(len(calls), 1)

    async def test_chat_only_plan_falls_back(self):
        state.engine().set_mode("active", True, state.now_ms())
        self.plans = [json.dumps({"steps": [{"id": "a", "capability": "chat.answer", "args": {"question": {"from": "literal", "value": "ciao"}}}]})]
        self.assertIsNone(await act.attempt("ciao", "guest", "it"))
        self.assertEqual(traces.recent(1)[0]["kind"], "fallback")

    def test_emergency_switch_forces_off(self):
        state.engine().set_mode("active", True, state.now_ms())
        state.save()
        state.reload()
        with mock.patch.dict("os.environ", {"NUXIVA_REASON_MODE": "off"}):
            self.assertFalse(act.active())
            self.assertEqual(json.loads(state.engine().status(0))["switch"]["mode"], "off")


class ApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "owner"
        patcher = mock.patch.object(api, "require_permission", lambda *a, **k: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)

    def test_status_without_native(self):
        with mock.patch.object(state, "ready", lambda: False):
            self.assertEqual(self.client.get("/api/v5/reasoning/status").json(), {"native": False})

    def test_unauthenticated_is_refused(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        self.assertEqual(TestClient(app).get("/api/v5/reasoning/status").status_code, 401)

    def test_emergency_switch_blocks_activation(self):
        with mock.patch.dict("os.environ", {"NUXIVA_REASON_MODE": "off"}), mock.patch.object(state, "engine", mock.Mock()):
            response = self.client.post("/api/v5/reasoning/mode", json={"mode": "active", "force": True})
        self.assertEqual(response.status_code, 409)

    def test_config_is_validated(self):
        self.assertEqual(self.client.put("/api/v5/reasoning/config", json={"retrieve_limit": 0}).status_code, 422)


if __name__ == "__main__":
    asyncio.run(unittest.main())
