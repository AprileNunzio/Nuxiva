import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from agenti.agent import registry
from agenti.team import learning, reasoning
from agenti.team.ceo import CEOExecutive
from agenti.team.fascicoli import formato, motore
from agenti.team.fascicoli.scrivano import Scrivano, texts


class ScrivanoTest(unittest.TestCase):
    def setUp(self):
        learning.reset()
        self.root = Path(tempfile.mkdtemp()) / "fascicoli"
        self.ceo = CEOExecutive()

    def tearDown(self):
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def _run(self, text: str, reply: str, native: bool, status: str = "success"):
        writer = Scrivano(self.root, native=native)
        with mock.patch("agenti.team.fascicoli.scrivano.scrivano", writer), \
                mock.patch.object(reasoning, "needs_reasoning", return_value=False):
            decision = asyncio.run(self.ceo.decide(text, {"lang": "it"}))
            result = self.ceo.synthesize(decision, {"reply": reply, "status": status, "verified": True, "agent": decision.primary_agent.id})
        return writer, decision, result

    def _engines(self):
        return (False, True) if motore.ENGINE == "rust" else (False,)

    def test_lampo_writes_request_and_outcome(self):
        for native in self._engines():
            with self.subTest(native=native):
                writer, decision, result = self._run("che tempo fa domani", "Sole e 20 gradi.", native)
                self.assertEqual(decision.level, "lampo")
                rel = decision.dossier["rel"]
                self.assertEqual(result["ceo"]["dossier"], decision.dossier["id"])
                report = writer.store().verify(rel)
                self.assertTrue(report["ok"] and report["complete"], report)
                self.assertEqual(report["files"], ["00-richiesta.md", "99-esito.md"])
                esito = writer.store().read(rel, "99-esito.md")
                self.assertIn("Sole e 20 gradi.", next(s["body"] for s in esito["sections"] if s["anchor"] == "answer"))
                self.assertEqual(formato.get(esito, "livello"), "lampo")

    def test_standard_writes_context_and_plan(self):
        for native in self._engines():
            with self.subTest(native=native):
                writer, decision, _ = self._run("Mi mostri una medusa", "Ecco la medusa.", native)
                self.assertEqual(decision.level, "standard")
                report = writer.store().verify(decision.dossier["rel"])
                self.assertTrue(report["ok"] and report["complete"], report)
                piano = writer.store().read(decision.dossier["rel"], "02-piano.md")
                steps = next(s["body"] for s in piano["sections"] if s["anchor"] == "steps")
                self.assertIn("[x] 01 · particles", steps)
                self.assertEqual(piano["title"], texts("it")["titles"]["piano"])

    def test_private_answers_are_sealed(self):
        writer, decision, _ = self._run("quanti battiti ho", "Il tuo battito è 61 bpm.", False)
        self.assertEqual(decision.primary_agent.id, "medico")
        text = (self.root / decision.dossier["rel"] / "99-esito.md").read_text(encoding="utf-8")
        self.assertNotIn("61 bpm", text)
        self.assertIn("impronta", text)

    def test_secrets_never_reach_disk(self):
        writer, decision, _ = self._run("che tempo fa domani password: hunter2", "ok", False)
        for path in (self.root / decision.dossier["rel"]).iterdir():
            if path.suffix == ".md":
                self.assertNotIn("hunter2", path.read_text(encoding="utf-8"))

    def test_files_and_key_are_private(self):
        writer, decision, _ = self._run("che tempo fa domani", "ok", False)
        self.assertEqual(os.stat(self.root).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(self.root / ".chiave").st_mode & 0o777, 0o600)
        for path in (self.root / decision.dossier["rel"]).iterdir():
            self.assertEqual(os.stat(path).st_mode & 0o077, 0)
        os.chmod(self.root / ".chiave", 0o644)
        with self.assertRaises(PermissionError):
            Scrivano(self.root).store()

    def test_disabled_writes_nothing(self):
        with mock.patch.dict(os.environ, {"NUXIVA_FASCICOLI": "0"}):
            _, decision, result = self._run("che tempo fa domani", "ok", False)
        self.assertEqual(decision.dossier, {})
        self.assertNotIn("dossier", result["ceo"])

    def test_failures_never_break_the_answer(self):
        writer = Scrivano(self.root, native=False)
        with mock.patch.object(Scrivano, "store", side_effect=OSError("disco pieno")):
            decision = self.ceo.analyze_request("che tempo fa domani")
            self.assertEqual(writer.open(decision, "x", "it"), {})

    def _with_tools(self, text, calls, reply="Fatto.", sealed_agent=False):
        writer = Scrivano(self.root, native=False)

        async def main():
            decision = await self.ceo.decide(text, {"lang": "it"})
            for name, args in calls:
                try:
                    await registry.run(name, args)
                except RuntimeError:
                    pass
            return decision, self.ceo.synthesize(decision, {"reply": reply, "status": "success", "verified": True,
                                                            "agent": decision.primary_agent.id})

        registry.TOOLS["zz_ok"] = {"name": "zz_ok", "description": "t", "args": {"x": "t"}, "fn": lambda x="": f"risposta {x}",
                                   "confirm": False, "full_only": False, "agent": "", "verify": None, "precheck": None, "intent": None}

        def boom(x=""):
            raise RuntimeError("guasto password: hunter2")

        registry.TOOLS["zz_boom"] = dict(registry.TOOLS["zz_ok"], name="zz_boom", fn=boom)
        self.addCleanup(lambda: [registry.TOOLS.pop(n, None) for n in ("zz_ok", "zz_boom")])
        with mock.patch("agenti.team.fascicoli.scrivano.scrivano", writer), \
                mock.patch.object(reasoning, "needs_reasoning", return_value=False), \
                mock.patch("agenti.agent.registry.enabled", return_value=True):
            decision, result = asyncio.run(main())
        return writer, decision, result

    def test_tool_calls_become_step_files_and_a_passed_check(self):
        writer, decision, _ = self._with_tools("metti un po' di musica", [("zz_ok", {"x": "1", "nope": 2})])
        rel = decision.dossier["rel"]
        store = writer.store()
        report = store.verify(rel)
        self.assertTrue(report["ok"], report)
        self.assertIn("passi/01-zz-ok.md", report["files"])
        self.assertIn("90-verifica.md", report["files"])
        step = store.read(rel, "passi/01-zz-ok.md")
        by = {s["anchor"]: s["body"] for s in step["sections"]}
        self.assertIn("risposta 1", by["result"])
        self.assertNotIn("nope", by["tool"])
        self.assertIn("completato", by["status"])
        check = {s["anchor"]: s["body"] for s in store.read(rel, "90-verifica.md")["sections"]}
        self.assertIn("Verifica superata", check["verdict"])
        self.assertEqual(decision.dossier["verdict"], "superata")

    def test_failed_tool_fails_the_check_and_hides_secrets(self):
        writer, decision, _ = self._with_tools("metti un po' di musica", [("zz_ok", {"x": "1"}), ("zz_boom", {})])
        rel = decision.dossier["rel"]
        text = (self.root / rel / "passi" / "02-zz-boom.md").read_text(encoding="utf-8")
        self.assertNotIn("hunter2", text)
        self.assertIn("errore", text)
        self.assertEqual(decision.dossier["verdict"], "non_superata")
        self.assertTrue(writer.store().verify(rel)["ok"])

    def test_sealed_agents_keep_tool_data_private(self):
        writer, decision, _ = self._with_tools("accendi la luce del salotto", [("zz_ok", {"x": "61 bpm"})])
        text = (self.root / decision.dossier["rel"] / "passi" / "01-zz-ok.md").read_text(encoding="utf-8")
        self.assertNotIn("61 bpm", text)
        self.assertIn("impronta", text)

    def test_lampo_records_no_steps(self):
        writer, decision, _ = self._with_tools("che tempo fa domani", [("zz_ok", {"x": "1"})])
        self.assertEqual(decision.level, "lampo")
        self.assertFalse((self.root / decision.dossier["rel"] / "passi").exists())

    def test_tools_without_a_dossier_are_untouched(self):
        async def main():
            return await registry.run("zz_ok", {"x": "2"})

        registry.TOOLS["zz_ok"] = {"name": "zz_ok", "description": "t", "args": {"x": "t"}, "fn": lambda x="": f"risposta {x}",
                                   "confirm": False, "full_only": False, "agent": "", "verify": None, "precheck": None, "intent": None}
        self.addCleanup(lambda: registry.TOOLS.pop("zz_ok", None))
        with mock.patch("agenti.agent.registry.enabled", return_value=True):
            self.assertEqual(asyncio.run(main()), "risposta 2")

    def test_listing_and_detail(self):
        from agenti.team.fascicoli import lettura
        writer, decision, _ = self._with_tools("metti un po' di musica", [("zz_ok", {"x": "1"})])
        self._run("che tempo fa domani", "ok", False)
        store = writer.store()
        items = lettura.listing(store, 10)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i["closed"] for i in items))
        mine = next(i for i in items if i["id"] == decision.dossier["id"])
        self.assertTrue(mine["checked"])
        self.assertIn("musica", mine["request"].lower())
        detail = lettura.detail(store, decision.dossier["rel"])
        self.assertIn("passi/01-zz-ok.md", detail["files"])
        with self.assertRaises(Exception):
            lettura.detail(store, "2020/01/01/20200101-000000-abcdef")
        with self.assertRaises(Exception):
            lettura.detail(store, "../../etc")

    def test_every_language_has_every_text(self):
        keys = {k: set(v) for k, v in texts("it").items()}
        for lang in ("en", "fr", "es"):
            self.assertEqual({k: set(v) for k, v in texts(lang).items()}, keys)
        for anchors in formato.SECTIONS.values():
            self.assertTrue(set(anchors) <= keys["headings"])


class FascicoliApiTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()) / "fascicoli"
        self.writer = Scrivano(self.root, native=False)
        self.addCleanup(shutil.rmtree, self.root.parent, ignore_errors=True)
        decision = CEOExecutive().analyze_request("che tempo fa domani")
        handle = self.writer.open(decision, "che tempo fa domani", "it")
        self.writer.close(handle, decision, {"reply": "Sole."}, {"status": "completed", "verified": True}, "Meteo")
        self.rel = handle["rel"]
        self.client = TestClient(nuxiva_supervisor.admin)
        self.patch = mock.patch("agenti.team.fascicoli.scrivano.scrivano", self.writer)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def _login(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers={"X-Nuxiva-Request": "1"})

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/fascicoli").status_code, 401)
        self.assertEqual(self.client.get(f"/api/fascicoli/{self.rel}").status_code, 401)

    def test_list_and_detail(self):
        self._login()
        items = self.client.get("/api/fascicoli?limit=5").json()["items"]
        self.assertEqual([i["rel"] for i in items], [self.rel])
        self.assertEqual(items[0]["level"], "lampo")
        detail = self.client.get(f"/api/fascicoli/{self.rel}").json()
        self.assertTrue(detail["report"]["ok"])
        self.assertIn("99-esito.md", detail["files"])

    def test_bad_input(self):
        self._login()
        self.assertEqual(self.client.get("/api/fascicoli?limit=0").status_code, 422)
        self.assertEqual(self.client.get("/api/fascicoli?limit=101").status_code, 422)
        self.assertEqual(self.client.get("/api/fascicoli/2020/01/01/20200101-000000-abcdef").status_code, 404)
        self.assertEqual(self.client.get("/api/fascicoli/2026/11/12/..%2F..%2Fx").status_code, 404)
        self.assertEqual(self.client.get("/api/fascicoli/2026/11/12/x").status_code, 404)


if __name__ == "__main__":
    unittest.main()
