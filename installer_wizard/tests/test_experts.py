import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agent import agent as agent_module
from features.agent import registry
from features.experts import live, routing, service, store as store_module, templates, tools
from features.experts.model import ExpertError, build, slug
from features.team.board import board

HEADERS = {"X-Nuxiva-Request": "1"}


class IsolatedStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(store_module, "PROFILES", base / "experts.json"),
            mock.patch.object(store_module, "HISTORY", base / "experts_history.sealed"),
            mock.patch.object(store_module, "HISTORY_KEY", base / "experts_history.key"),
        ]
        for p in self.patches:
            p.start()
        self.store = store_module.ExpertStore()
        self.swap = mock.patch.object(store_module, "experts", self.store)
        self.swap.start()
        self.service_swap = mock.patch.object(service, "experts", self.store)
        self.service_swap.start()
        from features.experts import api as api_module, commands as commands_module
        for module in (api_module, commands_module):
            swap = mock.patch.object(module, "experts", self.store)
            swap.start()
            self.addCleanup(swap.stop)
        self.base = base

    def tearDown(self):
        self.service_swap.stop()
        self.swap.stop()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()


class ModelTest(unittest.TestCase):
    def test_build_sanitizes_and_rejects_unknown_tools(self):
        expert = build({"id": "marco", "name": " Marco <b> ", "role": "Sysadmin", "specialty": "Debian\x00 server",
                        "knowledge": ["apt", "", "<script>"], "tools": ["debian_status"]}, {"debian_status"})
        self.assertEqual(expert.name, "Marco b")
        self.assertEqual(expert.specialty, "Debian server")
        self.assertEqual(expert.knowledge, ["apt", "script"])
        with self.assertRaises(ExpertError):
            build({"id": "marco", "name": "Marco", "role": "Sysadmin", "specialty": "Debian", "tools": ["rm_everything"]}, set())
        with self.assertRaises(ExpertError):
            build({"id": "../x", "name": "Marco", "role": "Sysadmin", "specialty": "Debian"}, set())

    def test_slug(self):
        self.assertEqual(slug("Lùca Rossi"), "luca-rossi")
        self.assertTrue(slug("Al").startswith("esperto"))


class TemplatesTest(unittest.TestCase):
    def test_every_language_has_every_template(self):
        for lang in templates.LANGS:
            data = json.loads((templates.LANG_DIR / f"{lang}.json").read_text(encoding="utf-8"))
            for tid in templates.SPECS:
                block = data["templates"][tid]
                self.assertTrue(block["name"] and block["role"] and block["specialty"] and block["knowledge"], (lang, tid))

    def test_template_tools_exist(self):
        for spec in templates.SPECS.values():
            for name in spec["tools"]:
                self.assertIn(name, registry.TOOLS)

    def test_blueprint_localized(self):
        self.assertEqual(templates.blueprint("debian", "en", "x")["role"], "Debian system administrator")
        self.assertEqual(templates.blueprint("football", "xx", "x")["role"], "Esperto di calcio")


class StoreTest(IsolatedStore):
    def test_create_persist_history_encrypted(self):
        expert = service.create({"template": "debian"}, "it", "test")
        self.assertEqual(expert.live, "debian")
        self.assertEqual(store_module.PROFILES.stat().st_mode & 0o777, 0o600)
        self.store.remember(expert.id, "user", "segreto-della-casa")
        raw = store_module.HISTORY.read_bytes()
        self.assertNotIn(b"segreto-della-casa", raw)
        fresh = store_module.ExpertStore()
        self.assertEqual(fresh.get(expert.id).name, expert.name)
        self.assertEqual(fresh.history(expert.id)[0]["text"], "segreto-della-casa")
        second = service.create({"template": "debian"}, "it", "test")
        self.assertNotEqual(second.id, expert.id)
        service.delete(expert.id)
        with self.assertRaises(KeyError):
            self.store.get(expert.id)

    def test_update_keeps_identity(self):
        expert = service.create({"name": "Giulia", "role": "Chef", "specialty": "cucina italiana"}, "it", "test")
        updated = service.update(expert.id, {"id": "altro", "instructions": "Ricette veloci", "enabled": False})
        self.assertEqual(updated.id, expert.id)
        self.assertFalse(updated.enabled)


class RoutingTest(IsolatedStore):
    def test_addressing_and_explicit_request(self):
        debian = service.create({"template": "debian"}, "it", "t")
        football = service.create({"template": "football"}, "it", "t")
        rows = self.store.all()
        self.assertEqual(routing.route(rows, "Marco, come sta il server?").id, debian.id)
        self.assertEqual(routing.route(rows, "chiedi all'esperto la classifica di serie a").id, football.id)
        self.assertEqual(routing.route(rows, "chiedi all'esperto perché apt non aggiorna i pacchetti").id, debian.id)
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
        self.assertIn(tools, agent_module.MODULES)
        for name in ("expert_ask", "expert_create", "debian_status", "football_scores"):
            self.assertEqual(registry.TOOLS[name]["agent"], "experts")


class ReasoningLoopTest(IsolatedStore):
    def setUp(self):
        super().setUp()
        from features.authz.principal import SYSTEM, act_as, current
        self.token = act_as(SYSTEM)
        self.addCleanup(current.reset, self.token)

    def test_tool_then_answer(self):
        expert = service.create({"template": "debian"}, "it", "t")
        replies = [{"tool": "apt_upgradable", "args": {}}, {"answer": "Il sistema è aggiornato."}]
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(side_effect=replies)), \
                mock.patch.object(live, "upgradable", mock.AsyncMock(return_value={"count": 0, "security": 0, "packages": []})):
            out = asyncio.run(service.ask(expert.id, "ci sono aggiornamenti?", "it"))
        self.assertEqual(out["text"], "Il sistema è aggiornato.")
        self.assertEqual(out["steps"][0]["result"], "il sistema è aggiornato")
        self.assertEqual([t["role"] for t in self.store.history(expert.id)], ["user", "expert"])
        self.assertTrue(any(m["from"] == service.board_key(expert.id) for m in board.messages))

    def test_unassigned_tool_is_refused(self):
        expert = service.create({"template": "football"}, "it", "t")
        replies = [{"tool": "run_command", "args": {"command": "ls"}}, {"answer": "Non posso."}]
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(side_effect=replies)):
            out = asyncio.run(service.ask(expert.id, "esegui ls", "it"))
        self.assertIn("non assegnato", out["steps"][0]["result"])

    def test_risky_tool_waits_for_confirmation(self):
        expert = service.create({"template": "debian"}, "it", "t")
        replies = [{"tool": "run_command", "args": {"command": "apt-get update"}}]
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(side_effect=replies)):
            out = asyncio.run(service.ask(expert.id, "aggiorna gli indici", "it"))
        self.assertEqual(out["pending"]["tool"], "run_command")
        self.assertEqual(service.pending(expert.id)["args"]["command"], "apt-get update")
        with mock.patch("features.brain.llm.generate", mock.AsyncMock(return_value={"answer": "Annullato come richiesto."})):
            done = asyncio.run(service.confirm(expert.id, False))
        self.assertIn("NEGATO", done["steps"][0]["result"])
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
        self.assertEqual({t["id"] for t in overview["templates"]}, {"debian", "football"})
        self.assertFalse(any(t["name"].startswith("expert_") for t in overview["tools"]))
        created = self.client.post("/api/experts", json={"template": "debian"}, headers=HEADERS)
        self.assertEqual(created.status_code, 200)
        eid = created.json()["id"]
        bad = self.client.post("/api/experts", json={"name": "X"}, headers=HEADERS)
        self.assertEqual(bad.status_code, 400)
        panel = self.client.get(f"/api/experts/{eid}/live", headers=HEADERS).json()
        self.assertEqual(panel["data"]["kind"], "debian")
        self.assertIn("memory", panel["data"])
        self.assertEqual(self.client.put(f"/api/experts/{eid}", json={"tools": ["nope"]}, headers=HEADERS).status_code, 400)
        self.assertEqual(self.client.get("/api/experts/..%2Fetc/live", headers=HEADERS).status_code, 404)
        self.assertEqual(self.client.post(f"/api/experts/{eid}/confirm", json={"yes": True}, headers=HEADERS).status_code, 409)
        self.assertEqual(self.client.delete(f"/api/experts/{eid}", headers=HEADERS).status_code, 200)
        self.assertEqual(self.client.get(f"/api/experts/{eid}/history", headers=HEADERS).status_code, 404)


if __name__ == "__main__":
    unittest.main()
