import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from agenti.agency import client as client_module
from agenti.agency.foresight import scenario, service
from agenti.agency.memory import ProjectMemory
from agenti.agency.words import LANGUAGES, dictionary

HEADERS = {"X-Nuxiva-Request": "1"}

WORLD = {
    "title": "Nuovo ponte‮",
    "entities": [
        {"key": "Comune", "name": "Comune di Riva", "kind": "ente"},
        {"key": "residenti", "name": "Residenti", "kind": "gruppo"},
        {"key": "comune", "name": "Duplicato", "kind": "ente"},
        {"name": ""},
    ],
    "relations": [
        {"from": "comune", "to": "residenti", "kind": "governa", "weight": 7},
        {"from": "residenti", "to": "comune", "kind": "doppione", "weight": 0.1},
        {"from": "comune", "to": "fantasma", "weight": 0.5},
    ],
    "actors": [
        {"name": "Sindaca Rossi", "role": "sindaca", "entity": "Comune di Riva", "count": 1,
         "persona": "Guida la giunta", "stance": 0.8, "influence": 0.9, "activity": "nan"},
        {"name": "Pendolari", "role": "residente", "entity": "residenti", "count": 500,
         "persona": "Usano il ponte ogni giorno", "stance": -0.2, "openness": 3},
        {"name": "Commercianti", "role": "commerciante", "count": 500, "stance": float("inf")},
        {"name": ""},
    ],
    "events": [
        {"round": 3, "title": "Costi pubblicati", "shift": -0.6, "reach": 0.7, "target": "residenti"},
        {"round": 999, "title": "Fuori tempo"},
        {"round": "x", "title": "Rotto"},
    ],
}


class FakeForesight:
    def __init__(self) -> None:
        self.sims: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []

    async def call(self, op: str, **fields):
        self.calls.append((op, fields))
        return getattr(self, op)(**fields)

    def foresight_create(self, id, scenario):
        self.sims[id] = {"scenario": scenario, "round": 0}
        return {"id": id, "title": scenario["title"], "round": 0, "rounds": scenario["rounds"]}

    def foresight_run(self, id, rounds=None):
        sim = self.sims[id]
        sim["round"] = min(sim["scenario"]["rounds"], sim["round"] + 10)
        return {"advanced": 10, "finished": sim["round"] >= sim["scenario"]["rounds"], "summary": {"id": id}}

    def foresight_report(self, id):
        if id not in self.sims:
            raise client_module.AgencyRejected("not_found", "project not found")
        sim = self.sims[id]
        report = {"question": sim["scenario"]["question"], "round": sim["round"], "rounds": sim["scenario"]["rounds"],
                  "agents": len(sim["scenario"]["agents"]), "outcome": {"leaning": "oppose"},
                  "trajectory": [{"round": r, "mean": 0} for r in range(sim["round"] + 1)], "roles": [],
                  "entities": [], "events": sim["scenario"]["events"], "influencers": [], "movers": [], "notable": []}
        return {"report": report, "ensemble": sim.get("ensemble")}

    def foresight_inject(self, id, event):
        self.sims[id]["scenario"]["events"].append(event)
        return {"id": id}

    def foresight_ensemble(self, id, runs):
        self.sims[id]["ensemble"] = {"runs": runs}
        return {"id": id, "ensemble": {"runs": runs}}

    def foresight_agent(self, id, agent):
        match = next((a for a in self.sims[id]["scenario"]["agents"] if a["key"] == agent), None)
        if match is None:
            raise client_module.AgencyRejected("not_found", "agent not found")
        return {"key": agent, "name": match["name"], "stance": match["traits"]["stance"], "memory": []}

    def foresight_list(self):
        return [{"id": k} for k in self.sims]

    def foresight_delete(self, id):
        self.sims.pop(id)
        return {"deleted": id}


def scripted(*replies):
    queue = list(replies)

    async def generate(prompt, **kwargs):
        if not queue:
            raise service.BrainUnavailable("script finished")
        return queue.pop(0)
    return generate


class ScenarioTest(unittest.TestCase):
    def setUp(self):
        self.spec, self.personas = scenario.build(WORLD, "Il ponte sarà accolto bene?", 120, 24, 5)

    def test_entities_relations_and_events_are_sanitised(self):
        keys = [e["key"] for e in self.spec["entities"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(self.spec["relations"]), 1)
        self.assertEqual(self.spec["relations"][0]["weight"], 1)
        self.assertEqual([e["round"] for e in self.spec["events"]], [3])
        self.assertNotIn("‮", self.spec["title"])

    def test_population_is_scaled_and_traits_bounded(self):
        agents = self.spec["agents"]
        self.assertLessEqual(len(agents), 120)
        self.assertEqual(len({a["key"] for a in agents}), len(agents))
        for agent in agents:
            for name, value in agent["traits"].items():
                low = -1 if name == "stance" else 0
                self.assertTrue(low <= value <= 1, (name, value))
            self.assertNotIn(agent["key"], agent["follows"])
        mayor = next(a for a in agents if a["name"] == "Sindaca Rossi")
        self.assertEqual(mayor["traits"]["stance"], 0.8)
        self.assertEqual(self.personas[mayor["key"]], "Guida la giunta")

    def test_work_budget_limits_population(self):
        spec, _ = scenario.build(WORLD, "Domanda lunga abbastanza", 2000, 720, 1)
        self.assertLessEqual(len(spec["agents"]) * 720, scenario.WORK)

    def test_garbage_gives_no_world(self):
        self.assertEqual(scenario.build("rotto", "Domanda valida?", 50, 10, 1), ({}, {}))
        self.assertEqual(scenario.build({"actors": [{"name": "Solo", "count": 1}]}, "Domanda?", 50, 10, 1), ({}, {}))

    def test_future_events_only(self):
        aliases = scenario.aliases_of(self.spec["entities"])
        self.assertIsNone(scenario.event_spec({"round": 2, "title": "x"}, 24, aliases, 5))
        event = scenario.event_spec({"round": 6, "title": "Nuovo fondo", "shift": 2, "target": "Residenti"},
                                    24, aliases, 5)
        self.assertEqual(event["shift"], 1)
        self.assertEqual(event["target"], "residenti")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = FakeForesight()
        for patcher in (mock.patch.object(service, "client", self.fake),
                        mock.patch.object(service, "memory", ProjectMemory(self.tmp)),
                        mock.patch.object(service.store, "event")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def create(self):
        with mock.patch("agenti.brain.llm.generate", scripted(WORLD)):
            return asyncio.run(service.create("Il comune annuncia un nuovo ponte sul fiume.",
                                              "Il ponte sarà accolto bene?", "it", 80, 30))

    def test_create_simulate_report_chat_and_delete(self):
        summary = self.create()
        sim_id = summary["id"]
        result = asyncio.run(service.simulate(sim_id))
        self.assertTrue(result["finished"])
        detail = asyncio.run(service.detail(sim_id))
        self.assertIsNone(detail["narrative"])
        with mock.patch("agenti.brain.llm.generate", scripted("## Esito\nContrario")):
            narrated = asyncio.run(service.narrate(sim_id, "it"))
        self.assertIn("Esito", narrated["narrative"])
        self.assertEqual(asyncio.run(service.detail(sim_id))["narrative"], narrated["narrative"])
        asyncio.run(service.ensemble(sim_id, 999))
        self.assertTrue(asyncio.run(service.detail(sim_id))["narrative_stale"])
        key = self.fake.sims[sim_id]["scenario"]["agents"][0]["key"]
        with mock.patch("agenti.brain.llm.generate", scripted("Sono favorevole.")):
            reply = asyncio.run(service.chat(sim_id, key, "  Cosa\tne pensi?  ", "it"))
        self.assertEqual(reply["chat"][0]["text"], "Cosa ne pensi?")
        self.assertEqual(asyncio.run(service.agent(sim_id, key))["chat"][-1]["text"], "Sono favorevole.")
        asyncio.run(service.delete(sim_id))
        self.assertEqual(service.memory.load(sim_id), {})

    def test_bad_inputs_are_typed_failures(self):
        for material, question, code in (("corto", "Domanda valida?", "material"),
                                         ("Materiale abbastanza lungo davvero", "no", "question")):
            with self.assertRaises(service.ForesightFailure) as failure:
                asyncio.run(service.create(material, question, "it"))
            self.assertEqual(failure.exception.code, code)
        with mock.patch("agenti.brain.llm.generate", scripted({"actors": []})):
            with self.assertRaises(service.ForesightFailure) as failure:
                asyncio.run(service.create("Materiale abbastanza lungo davvero", "Domanda valida?", "it"))
        self.assertEqual(failure.exception.code, "empty_world")
        with mock.patch("agenti.brain.llm.generate", scripted()):
            with self.assertRaises(service.ForesightFailure) as failure:
                asyncio.run(service.create("Materiale abbastanza lungo davvero", "Domanda valida?", "it"))
        self.assertEqual(failure.exception.code, "brain")

    def test_inject_respects_the_current_round(self):
        sim_id = self.create()["id"]
        asyncio.run(service.simulate(sim_id))
        with self.assertRaises(service.ForesightFailure):
            asyncio.run(service.inject(sim_id, {"round": 5, "title": "Troppo tardi"}))
        self.fake.sims[sim_id]["round"] = 4
        asyncio.run(service.inject(sim_id, {"round": 6, "title": "Fondi europei", "shift": 0.7,
                                            "target": "Comune di Riva"}))
        self.assertEqual(self.fake.sims[sim_id]["scenario"]["events"][-1]["target"], "comune")

    def test_bad_agent_key_and_empty_message(self):
        sim_id = self.create()["id"]
        with self.assertRaises(service.ForesightFailure):
            asyncio.run(service.agent(sim_id, "../x"))
        with self.assertRaises(service.ForesightFailure):
            asyncio.run(service.chat(sim_id, "x", " \n ", "it"))


class LanguageTest(unittest.TestCase):
    def test_every_language_has_the_same_foresight_keys(self):
        base = dictionary("it")
        for lang in LANGUAGES:
            words = dictionary(lang)
            for group in ("foresight", "foresight_errors"):
                self.assertEqual(set(words[group]), set(base[group]), (lang, group))
        from agenti.agency.foresight.api import CODES
        self.assertEqual(set(CODES), set(base["foresight_errors"]))


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = TestClient(nuxiva_supervisor.admin)
        assert cls.admin.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"},
                              headers=HEADERS).status_code == 200

    def test_validation_and_offline_engine(self):
        r = self.admin.post("/api/agency/foresight", json={"material": "x", "question": "Domanda valida?"},
                            headers=HEADERS)
        self.assertEqual(r.json()["detail"]["code"], "material")
        offline = client_module.AgencyClient(Path(tempfile.mkdtemp()) / "none.sock", timeout=1)
        with mock.patch.object(service, "client", offline):
            r = self.admin.get("/api/agency/foresight", headers=HEADERS)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(self.admin.get("/api/agency/foresight/Bad..id", headers=HEADERS).status_code, 404)

    def test_requires_admin(self):
        anonymous = TestClient(nuxiva_supervisor.admin)
        self.assertIn(anonymous.get("/api/agency/foresight").status_code, (401, 403))
