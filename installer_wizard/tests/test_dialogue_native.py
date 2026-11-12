import sqlite3
from contextlib import closing
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import native_core

from agenti.chat import dialogue as dialogue_module
from agenti.chat.dialogue import Dialogue, PyBook, RustBook, make_turn
from agenti.chat.history import HistoryStore

ENGINE = native_core.symbol("RustDialogue")
NOW = 1_000_000.0

FOLLOW_UPS = ["e domani?", "e a Milano?", "e domani a Napoli?", "invece stasera?", "e tu come stai?", "anche sabato",
              "ed in Val d'Aosta?", "e tra 3 giorni?", "e il prossimo weekend?", "mentre a Torino?", "e?", "e dove"]
LAST_TURNS = [("che tempo fa a Roma?", "weather"), ("che tempo fa oggi?", "weather"), ("portami da Milano Centrale", "maps"),
              ("accendi la luce in cucina", "home"), ("raccontami una storia", "chat"), ("che ore sono a Tokyo domani?", "time")]


def books():
    return [PyBook(), RustBook(ENGINE(dialogue_module.STALE_SECONDS, dialogue_module.RESUME_SECONDS,
                                      dialogue_module.RECALL_SECONDS))]


@unittest.skipIf(ENGINE is None, "modulo nativo assente")
class DialogueParityTest(unittest.TestCase):

    def test_resolve_matches_python(self):
        for (text, intent) in LAST_TURNS:
            py, rs = books()
            for book in (py, rs):
                book.remember("kiosk", make_turn(text, "Ecco.", intent, NOW - 5))
            for follow in FOLLOW_UPS:
                with self.subTest(last=text, follow=follow):
                    self.assertEqual(rs.resolve("kiosk", follow, NOW), py.resolve("kiosk", follow, NOW))
        self.assertEqual(rs.resolve("kiosk", "e domani?", NOW), "che ore sono a Tokyo domani?")

    def test_timeline_matches_python(self):
        py, rs = books()
        ages = [9 * 3600, 3 * 3600 + 30, 3 * 3600, 20 * 60, 10 * 60, 50, 5]
        for i, age in enumerate(ages):
            who = "Nunzio" if i % 2 else ""
            reply = "Vuoi altro?" if i == len(ages) - 1 else f"Risposta {i}."
            for book in (py, rs):
                book.remember("kiosk", make_turn(f"frase numero {i}", reply, "chat", NOW - age, who))
        for later in (0, 30, 90, 11 * 60, 16 * 60, 4 * 3600, 7 * 3600, 30 * 3600):
            now = NOW + later
            with self.subTest(later=later):
                self.assertEqual(rs.recent("kiosk", now), py.recent("kiosk", now))
                self.assertEqual(rs.last("kiosk", now), py.last("kiosk", now))
                self.assertEqual(rs.asked_question("kiosk", now), py.asked_question("kiosk", now))
                self.assertAlmostEqual(rs.since_reply("kiosk", now), py.since_reply("kiosk", now), places=6)
                for query in ("", "che ore sono", "dove eravamo rimasti?", "Come dicevamo prima"):
                    self.assertEqual(rs.context("kiosk", now, query), py.context("kiosk", now, query))

    def test_resume_after_a_pause(self):
        _, rs = books()
        rs.remember("kiosk", make_turn("organizziamo la cena di sabato", "Per quante persone?", "chat", NOW - 2 * 3600, "Nunzio"))
        ctx = rs.context("kiosk", NOW, "")
        self.assertTrue(ctx.startswith("Conversazione ripresa dopo 120 minuti"))
        self.assertIn("Nunzio: organizziamo la cena di sabato", ctx)
        far = books()[1]
        far.remember("kiosk", make_turn("organizziamo la cena", "Certo.", "chat", NOW - 10 * 3600))
        self.assertEqual(far.context("kiosk", NOW, "accendi la luce"), "")
        self.assertIn("organizziamo la cena", far.context("kiosk", NOW, "di cosa stavamo parlando?"))

    def test_load_and_limits(self):
        py, rs = books()
        stored = [make_turn(f"t{i}", "r", "chat", NOW - 100 + i) for i in range(10)]
        for book in (py, rs):
            book.remember("kiosk", make_turn("ultimo", "r", "chat", NOW))
            book.load("kiosk", stored)
        self.assertEqual(rs.recent("kiosk", NOW), py.recent("kiosk", NOW))
        self.assertEqual(len(rs.recent("kiosk", NOW)), dialogue_module.KEEP)
        with self.assertRaises(ValueError):
            rs.remember("bad\x00device", make_turn("x", "y", "chat", NOW))
        with self.assertRaises(ValueError):
            rs.engine.resolve("kiosk", "x" * 20000, NOW)


class DialogueStoreTest(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "dialogue.db"
        self.store = HistoryStore(self.path)
        patcher = mock.patch.object(dialogue_module, "history", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_history_is_encrypted_at_rest(self):
        Dialogue().remember("kiosk", "il mio codice è 4512", "Lo ricorderò.", "chat", "Nunzio")
        with closing(sqlite3.connect(self.path)) as conn:
            raw = conn.execute("SELECT text, reply, who FROM turns").fetchone()
        self.assertTrue(all(v.startswith("s1:") for v in raw))
        self.assertNotIn("4512", "".join(raw))
        self.assertEqual(oct(self.path.with_name("dialogue.key").stat().st_mode & 0o777), "0o600")
        last = Dialogue().last("kiosk")
        self.assertEqual((last.text, last.who), ("il mio codice è 4512", "Nunzio"))

    def test_legacy_plain_rows_and_old_schema_are_read(self):
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE turns (device TEXT NOT NULL, text TEXT NOT NULL, reply TEXT NOT NULL, "
                     "intent TEXT NOT NULL, at REAL NOT NULL)")
        conn.execute("INSERT INTO turns VALUES (?, ?, ?, ?, ?)", ("kiosk", "che tempo fa a Roma?", "Sole.", "weather", time.time()))
        conn.commit()
        conn.close()
        d = Dialogue()
        self.assertEqual(d.resolve("kiosk", "e domani?"), "che tempo fa a Roma domani?")
        d.remember("kiosk", "grazie", "Prego.", "chat")
        self.assertEqual(len(self.store.recent("kiosk", 0, 10)), 2)

    def test_rows_sealed_with_another_key_are_skipped(self):
        Dialogue().remember("kiosk", "segreto", "ok", "chat")
        self.path.with_name("dialogue.key").unlink()
        fresh = HistoryStore(self.path)
        self.assertEqual(fresh.recent("kiosk", 0, 10), [])
        self.assertFalse(fresh.broken)

    def test_forget_clears_memory(self):
        d = Dialogue()
        d.remember("kiosk", "ciao", "ciao!", "chat")
        d.forget()
        self.store.forget()
        self.assertIsNone(d.last("kiosk"))

    def test_python_fallback_when_native_missing(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            d = Dialogue()
        self.assertIsInstance(d.book, PyBook)
        d.remember("kiosk", "che tempo fa a Roma?", "Sole.", "weather")
        self.assertEqual(d.resolve("kiosk", "e domani?"), "che tempo fa a Roma domani?")


if __name__ == "__main__":
    unittest.main()
