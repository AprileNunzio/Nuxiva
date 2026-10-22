import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agent import tool_scanner
from features.agent import registry
from features.experts import live, routing, service, skills, store as store_module, templates, tools
from features.experts.model import ExpertError, build, slug
from features.team.board import board

HEADERS = {"X-Nuxiva-Request": "1"}


class IsolatedStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        for name, path in (("PROFILES", "experts.json"), ("HISTORY", "experts_history.sealed"), ("HISTORY_KEY", "experts_history.key"), ("SEEDED", "experts_seeded.json")):
            patch = mock.patch.object(store_module, name, base / path)
            patch.start()
            self.addCleanup(patch.stop)
        self.store = store_module.ExpertStore()
        from features.experts import api as api_module, commands as commands_module
        for module in (store_module, service, api_module, commands_module):
            swap = mock.patch.object(module, "experts", self.store)
            swap.start()
            self.addCleanup(swap.stop)


class ModelTest(unittest.TestCase):
    def test_build_sanitizes_and_has_no_personal_name(self):
        expert = build({"id": "sysadmin", "name": "Marco", "role": " Sysadmin <b> ", "specialty": "Debian\x00 server",
                        "knowledge": ["apt", "", "<script>"], "tools": ["debian_status"]}, {"debian_status"})
        self.assertEqual(expert.role, "Sysadmin b")
        self.assertFalse(hasattr(expert, "name"))
        self.assertNotIn("name", expert.to_dict())
        self.assertEqual(expert.specialty, "Debian server")
        self.assertEqual(expert.knowledge, ["apt", "script"])
        with self.assertRaises(ExpertError):
            build({"id": "sysadmin", "role": "Sysadmin", "specialty": "Debian", "tools": ["rm_everything"]}, set())
        with self.assertRaises(ExpertError):
            build({"id": "sysadmin", "role": "Sysadmin", "specialty": "Debian", "skills": ["hack_all"]}, set())
        with self.assertRaises(ExpertError):
            build({"id": "../x", "role": "Sysadmin", "specialty": "Debian"}, set())

    def test_skills_bring_their_tools(self):
        expert = build({"id": "sysadmin", "role": "Sysadmin", "specialty": "Debian", "skills": ["log_analysis"]}, set(registry.TOOLS))
        self.assertEqual(expert.skills, ["log_analysis"])
        self.assertIn("debian_logs", expert.tools)

    def test_slug(self):
        self.assertEqual(slug("Esperto di calcio"), "esperto-di-calcio")
        self.assertTrue(slug("Al").startswith("esperto"))


class CatalogTest(unittest.TestCase):
    def test_every_language_has_templates_and_skills(self):
        for lang in templates.LANGS:
            data = json.loads((templates.LANG_DIR / f"{lang}.json").read_text(encoding="utf-8"))
            for tid in templates.SPECS:
                block = data["templates"][tid]
                self.assertNotIn("name", block)
                self.assertTrue(block["role"] and block["specialty"] and block["knowledge"], (lang, tid))
            for sid in skills.SKILLS:
                block = data["skills"][sid]
                self.assertTrue(block["name"] and block["purpose"] and block["procedure"] and block["rules"], (lang, sid))

    def test_tools_exist(self):
        for spec in templates.SPECS.values():
            for name in spec["tools"]:
                self.assertIn(name, registry.TOOLS)
            for sid in spec["skills"]:
                self.assertTrue(set(skills.tools_of(sid)) <= set(spec["tools"]), sid)
        for spec in skills.SKILLS.values():
            for name in spec["tools"]:
                self.assertIn(name, registry.TOOLS)

    def test_blueprint_localized(self):
        self.assertEqual(templates.blueprint("debian", "en", "x")["role"], "Debian expert")
        self.assertEqual(templates.blueprint("football", "xx", "x")["role"], "Esperto di calcio")

    def test_suggest_and_briefing(self):
        self.assertEqual(skills.suggest(["system_health", "security_updates"], "ci sono aggiornamenti di sicurezza?"), "security_updates")
        self.assertIsNone(skills.suggest(["standings"], "ciao"))
        self.assertIn("football_table", skills.briefing("standings", "it"))


class StoreTest(IsolatedStore):
    def test_create_persist_history_encrypted(self):
        expert = service.create({"template": "debian"}, "it", "test")
        self.assertEqual(expert.live, "debian")
        self.assertEqual(expert.id, "esperto-debian")
        self.assertEqual(store_module.PROFILES.stat().st_mode & 0o777, 0o600)
        self.store.remember(expert.id, "user", "segreto-della-casa")
        self.assertNotIn(b"segreto-della-casa", store_module.HISTORY.read_bytes())
        fresh = store_module.ExpertStore()
        self.assertEqual(fresh.get(expert.id).skills, expert.skills)
        self.assertEqual(fresh.history(expert.id)[0]["text"], "segreto-della-casa")
        second = service.create({"template": "debian"}, "it", "test")
        self.assertNotEqual(second.id, expert.id)
        service.delete(expert.id)
        with self.assertRaises(KeyError):
            self.store.get(expert.id)

    def test_update_keeps_identity(self):
        expert = service.create({"role": "Chef", "specialty": "cucina italiana"}, "it", "test")
        updated = service.update(expert.id, {"id": "altro", "instructions": "Ricette veloci", "enabled": False})
        self.assertEqual(updated.id, expert.id)
        self.assertFalse(updated.enabled)


class RoutingTest(IsolatedStore):
    def test_addressing_and_explicit_request(self):
        debian = service.create({"template": "debian"}, "it", "t")
        football = service.create({"template": "football"}, "it", "t")
        rows = self.store.all()
        self.assertEqual(routing.route(rows, "Esperto Debian, come sta il server?").id, debian.id)
        self.assertEqual(routing.route(rows, "chiedi all'esperto di calcio chi ha vinto").id, football.id)
        self.assertEqual(routing.route(rows, "chiedi all'esperto la classifica di serie a").id, football.id)
        self.assertEqual(routing.route(rows, "chiedi all'esperto perché apt non aggiorna i pacchetti").id, debian.id)
        self.assertIsNone(routing.route(rows, "Marco, come stai?"))
        self.assertIsNone(routing.route(rows, "che tempo fa domani"))


class ToolsTest(unittest.TestCase):
    def test_debian_status_reads_real_system(self):
        out = asyncio.run(tools.debian_status())
        self.assertIn("sistema:", out)
        self.assertIn("memoria:", out)

    def test_unit_names_are_validated(self):
        with self.assertRaises(ValueError):
            asyncio.run(tools.debian_service("ssh; rm -rf /"))
        with self.assertRaises(ValueError):
            asyncio.run(tools.debian_logs(unit="--help"))

    def test_football_table_uses_source(self):
        rows = [{"rank": 1, "name": "Napoli", "points": 20, "played": 8, "won": 6, "drawn": 2, "lost": 0, "diff": 9}]
        with mock.patch("features.sports.football.standings", mock.AsyncMock(return_value=rows)):
            out = asyncio.run(tools.football_table("ita.1"))
        self.assertIn("1. Napoli 20 pt", out)
        with self.assertRaises(ValueError):
            asyncio.run(tools.football_table("xyz"))

    def test_tools_registered_to_main_agent(self):
        self.assertEqual(tool_scanner.loaded().get("features.experts.tools"), "experts")
        for name in ("expert_ask", "expert_create", "debian_status", "football_scores"):
            self.assertEqual(registry.TOOLS[name]["agent"], "experts")


class AgentLoopTest(IsolatedStore):
    def setUp(self):
        super().setUp()
        from features.authz.principal import SYSTEM, act_as, current
        token = act_as(SYSTEM)
        self.addCleanup(current.reset, token)

    def _ask(self, expert_id, question, replies):
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(side_effect=replies)) as brain:
            out = asyncio.run(service.ask(expert_id, question, "it"))
        return out, brain

    def test_skill_then_tool_then_answer(self):
        expert = service.create({"template": "debian"}, "it", "t")
        replies = [{"skill": "security_updates"}, {"tool": "apt_upgradable", "args": {}}, {"answer": "Il sistema è aggiornato."}]
        with mock.patch.object(live, "upgradable", mock.AsyncMock(return_value={"count": 0, "security": 0, "packages": []})):
            out, brain = self._ask(expert.id, "ci sono aggiornamenti?", replies)
        self.assertEqual(out["text"], "Il sistema è aggiornato.")
        self.assertEqual(out["steps"][0]["tool"], "skill:security_updates")
        self.assertEqual(out["steps"][1]["result"], "il sistema è aggiornato")
        first_prompt = brain.call_args_list[0].args[0]
        second_prompt = brain.call_args_list[1].args[0]
        self.assertIn("Competenza suggerita per questa domanda: security_updates", first_prompt)
        self.assertNotIn("apt_upgradable(", first_prompt)
        self.assertIn("apt_upgradable(", second_prompt)
        self.assertNotIn("debian_service(", second_prompt)
        self.assertEqual([t["role"] for t in self.store.history(expert.id)], ["user", "expert"])
        self.assertTrue(any(m["from"] == service.board_key(expert.id) and m["kind"] == "competenza" for m in board.messages))

    def test_tool_requires_its_skill(self):
        expert = service.create({"template": "debian"}, "it", "t")
        out, _ = self._ask(expert.id, "stato", [{"tool": "debian_status", "args": {}}, {"answer": "Serve la competenza."}])
        self.assertIn("attiva prima la competenza", out["steps"][0]["result"])

    def test_unknown_skill_and_unassigned_tool_refused(self):
        expert = service.create({"template": "football"}, "it", "t")
        out, _ = self._ask(expert.id, "esegui ls", [{"skill": "security_updates"}, {"tool": "run_command", "args": {"command": "ls"}}, {"answer": "Non posso."}])
        self.assertIn("non posseduta", out["steps"][0]["result"])
        self.assertIn("non assegnato", out["steps"][1]["result"])

    def test_risky_tool_waits_for_confirmation(self):
        expert = service.create({"template": "debian"}, "it", "t")
        out, _ = self._ask(expert.id, "aggiorna gli indici", [{"skill": "security_updates"}, {"tool": "run_command", "args": {"command": "apt-get update"}}])
        self.assertEqual(out["pending"]["tool"], "run_command")
        self.assertEqual(service.pending(expert.id)["args"]["command"], "apt-get update")
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(return_value={"answer": "Annullato come richiesto."})):
            done = asyncio.run(service.confirm(expert.id, False))
        self.assertIn("NEGATO", done["steps"][1]["result"])
        self.assertEqual(done["text"], "Annullato come richiesto.")
        self.assertIsNone(service.pending(expert.id))


class ApiTest(IsolatedStore):
    def setUp(self):
        super().setUp()
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def test_requires_login(self):
        self.assertEqual(TestClient(nuxiva_supervisor.admin).get("/api/experts").status_code, 401)

    def test_crud_and_live(self):
        overview = self.client.get("/api/experts", headers=HEADERS).json()
        self.assertEqual({t["id"] for t in overview["templates"]}, set(templates.ids()))
        self.assertTrue({"debian", "football", "teacher-math", "lawyer"} <= set(templates.ids()))
        self.assertEqual({s["id"] for s in overview["skills"]}, set(skills.SKILLS))
        self.assertFalse(any(t["name"].startswith("expert_") for t in overview["tools"]))
        created = self.client.post("/api/experts", json={"template": "debian"}, headers=HEADERS)
        self.assertEqual(created.status_code, 200)
        body = created.json()
        self.assertNotIn("name", body)
        eid = body["id"]
        self.assertEqual(self.client.post("/api/experts", json={"role": "X"}, headers=HEADERS).status_code, 400)
        panel = self.client.get(f"/api/experts/{eid}/live", headers=HEADERS).json()
        self.assertEqual(panel["data"]["kind"], "debian")
        self.assertIn("memory", panel["data"])
        self.assertEqual(self.client.put(f"/api/experts/{eid}", json={"tools": ["nope"]}, headers=HEADERS).status_code, 400)
        self.assertEqual(self.client.put(f"/api/experts/{eid}", json={"skills": ["standings"]}, headers=HEADERS).status_code, 200)
        self.assertEqual(self.client.get("/api/experts/..%2Fetc/live", headers=HEADERS).status_code, 404)
        self.assertEqual(self.client.post(f"/api/experts/{eid}/confirm", json={"yes": True}, headers=HEADERS).status_code, 409)
        self.assertEqual(self.client.delete(f"/api/experts/{eid}", headers=HEADERS).status_code, 200)
        self.assertEqual(self.client.get(f"/api/experts/{eid}/history", headers=HEADERS).status_code, 404)


if __name__ == "__main__":
    unittest.main()
