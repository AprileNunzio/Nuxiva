import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_every_language_has_every_text(self):
        keys = {k: set(v) for k, v in texts("it").items()}
        for lang in ("en", "fr", "es"):
            self.assertEqual({k: set(v) for k, v in texts(lang).items()}, keys)
        for anchors in formato.SECTIONS.values():
            self.assertTrue(set(anchors) <= keys["headings"])


if __name__ == "__main__":
    unittest.main()
