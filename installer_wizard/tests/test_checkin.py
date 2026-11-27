import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import native_core

from agenti.chat.checkin import compose, facts, service, sources
from agenti.chat.checkin.ledger import Affinity, Ledger, shingles, similarity

READY = native_core.symbol("checkin_plan") is not None
AGENTS = Path(__file__).resolve().parent.parent / "agenti"
SPORT_LANGUAGE = AGENTS / "sport" / "sports" / "language"
GOOGLE_LANGUAGE = AGENTS / "comunicazione" / "google" / "language"


def sample() -> list[dict]:
    match = dict(facts.fact("sport_1", "sport", "interest", 60, 900, "sport_today",
                            {"team": "Napoli", "rival": "Roma", "time": "20:45", "score": "0-0"},
                            starts_at=time.time() + 3600, terms=["partita", "Napoli"]), origin=str(SPORT_LANGUAGE))
    return [facts.fact("mesh_ok", "mesh", "ok", 30, 300, "mesh_ok", {"n": 4}, terms=facts.MESH_TERMS),
            dict(facts.fact("mail_none", "email", "ok", 25, 600, "mail_none"), origin=str(GOOGLE_LANGUAGE)),
            match]


class ComposeTests(unittest.TestCase):

    def test_lines_render_in_every_language(self):
        for lang in compose.LANGUAGES:
            for f in sample():
                self.assertTrue(compose.render(f, lang), (lang, f["line"]))

    def test_grounding_rejects_invented_numbers(self):
        by_key = {f["key"]: f for f in sample()}
        plan = {"facts": [{"key": "sport_1", "repeat": False}], "verified": ["mesh"], "verified_again": False}
        self.assertTrue(compose.grounded("Stasera alle 20:45 gioca il Napoli, 4 nodi regolari.", plan, by_key, 21))
        self.assertFalse(compose.grounded("Ha 12 email non lette.", plan, by_key, 21))

    def test_signatures_change_only_with_content(self):
        a = facts.fact("mail_unread", "email", "notice", 50, 600, "mail_unread", {"n": 3})
        b = facts.fact("mail_unread", "email", "notice", 50, 600, "mail_unread", {"n": 3})
        c = facts.fact("mail_unread", "email", "notice", 50, 600, "mail_unread", {"n": 4})
        self.assertEqual(a["signature"], b["signature"])
        self.assertNotEqual(a["signature"], c["signature"])


class LedgerTests(unittest.TestCase):

    def test_records_only_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Ledger(Path(tmp) / "turns.json")
            book.record(["abc"], "direct", False, "Tutto bene signore, nessuna email nuova.")
            raw = (Path(tmp) / "turns.json").read_text(encoding="utf-8")
            self.assertNotIn("email", raw)
            self.assertTrue(book.too_similar("Tutto bene signore, nessuna email nuova.", 0.75))
            self.assertFalse(book.too_similar("Stasera gioca il Napoli contro la Roma alle 20:45.", 0.75))

    def test_similarity_is_bounded(self):
        self.assertEqual(similarity(shingles("uno due tre"), shingles("uno due tre")), 1.0)
        self.assertEqual(similarity([], shingles("uno")), 0.0)


@unittest.skipUnless(READY, "modulo nativo non disponibile")
class CheckinTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Ledger(Path(self.tmp.name) / "turns.json")
        self.learned = Affinity(Path(self.tmp.name) / "affinity.json")
        self.patches = [mock.patch.object(service, "ledger", self.book),
                        mock.patch.object(service, "affinity", self.learned),
                        mock.patch.dict(service._pending, {"at": 0, "told": []}),
                        mock.patch.object(service, "_facts", mock.AsyncMock(return_value=sample()))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_small_talk_is_detected_and_tasks_are_not(self):
        for text in ("ciao jarvis come va? tutto bene?", "how are you?", "¿qué tal?", "comment ça va ?"):
            self.assertIsNotNone(service.detect(text), text)
        for text in ("che ore sono", "accendi la luce", "come va installato il server su windows"):
            self.assertIsNone(service.detect(text), text)

    def test_answer_uses_real_facts_and_never_invents(self):
        invented = mock.AsyncMock(return_value="Tutto bene, ha 37 email non lette.")
        with mock.patch("agenti.brain.llm.generate", invented):
            speech, ui = asyncio.run(service.answer("ciao jarvis come va? tutto bene?"))
        self.assertNotIn("37", speech)
        self.assertIn("Napoli", speech)
        self.assertEqual(ui, {"mode": "face"})

    def test_good_draft_is_kept(self):
        draft = "Tutto bene, signore: server e satelliti regolari e stasera alle 20:45 gioca il Napoli. Forza Napoli!"
        with mock.patch("agenti.brain.llm.generate", mock.AsyncMock(return_value=draft)):
            speech, _ = asyncio.run(service.answer("come va?"))
        self.assertIn("Forza Napoli", speech)

    def test_asking_again_soon_is_fast_and_different(self):
        draft = "Tutto bene, signore: stasera alle 20:45 gioca il Napoli."
        generate = mock.AsyncMock(return_value=draft)
        with mock.patch("agenti.brain.llm.generate", generate):
            first, _ = asyncio.run(service.answer("come va?"))
            second, _ = asyncio.run(service.answer("tutto bene?"))
        self.assertEqual(generate.await_count, 1)
        self.assertNotEqual(first, second)

    def test_following_up_teaches_what_interests_the_user(self):
        with mock.patch("agenti.brain.llm.generate", mock.AsyncMock(return_value="")):
            asyncio.run(service.answer("come va?"))
        learned = service.observe("a che ora gioca il Napoli?")
        self.assertTrue(learned["counted"])
        self.assertIn("sport", learned["engaged"])
        saved = {(e["topic"], e["when"]): e["weight"] for e in self.learned.load()}
        self.assertGreater(saved[("sport", "any")], 1.0)
        self.assertIsNone(service.observe("e poi?"))

    def test_not_small_talk_returns_none(self):
        self.assertIsNone(asyncio.run(service.answer("che tempo fa domani a Roma?")))


class SourcesTests(unittest.TestCase):

    def test_modules_with_a_briefing_join_by_themselves(self):
        names = {name for name, *_ in sources.discovered()}
        self.assertTrue({"sports", "google"} <= names, names)

    def test_malformed_facts_are_refused(self):
        good = facts.fact("x", "t", "info", 10, 60, "news", {"title": "a"})
        self.assertTrue(sources.valid(good))
        self.assertFalse(sources.valid(dict(good, kind="panic")))
        self.assertFalse(sources.valid(dict(good, params={"a": 1})))
        self.assertFalse(sources.valid("x"))

    def test_module_lines_come_from_the_module(self):
        match = sample()[2]
        for lang in compose.LANGUAGES:
            self.assertIn("Napoli", compose.render(match, lang), lang)


class FallbackTests(unittest.TestCase):

    def test_without_native_nothing_is_intercepted(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            self.assertIsNone(asyncio.run(service.answer("come va?")))


if __name__ == "__main__":
    unittest.main()
