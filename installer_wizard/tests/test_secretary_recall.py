import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from agenti.desktop import briefing, context, secretary
from agenti.desktop.recall import Recall, normalize, signature


class RecallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = [1000.0]
        self.recall = Recall(Path(self.tmp.name) / "recall.json", clock=lambda: self.now[0])

    def test_normalize_collapses_numbers(self):
        self.assertEqual(normalize("Telecamera A: recorder_exit 240 alle 10:31"), normalize("telecamera a: recorder_exit 240 alle 11:02"))

    def test_seen_card_survives_restart_and_expires(self):
        sig = signature("brief", {"lines": ["Aggiornamento disponibile"]}, True)
        self.recall.mark("systems", sig, None)
        again = Recall(Path(self.tmp.name) / "recall.json", clock=lambda: self.now[0])
        self.assertTrue(again.seen_card("systems", sig))
        self.assertFalse(again.seen_card("systems", signature("brief", {"lines": ["Servizio giù"]}, True)))
        self.now[0] += 7 * 3600
        self.assertFalse(again.seen_card("systems", sig))

    def test_known_lines(self):
        self.recall.mark("important", "x", ["Disco quasi pieno 91%"])
        self.assertIn(normalize("Disco quasi pieno 93%"), self.recall.known_lines())


class ImportantTest(unittest.TestCase):
    def test_only_new_lines_and_urgency_only_for_errors(self):
        now = datetime.now().isoformat()
        events = [{"level": "WARN", "msg": "Rete lenta 12 ms", "ts": now}, {"level": "WARN", "msg": "Disco al 90%", "ts": now}]
        with mock.patch.object(briefing.store, "events", events):
            wid, data, priority = briefing.important()
            self.assertEqual((len(data["lines"]), priority), (2, 50))
            _, data, _ = briefing.important(frozenset({normalize("Rete lenta 40 ms")}))
            self.assertEqual(data["lines"], ["Disco al 90%"])
            self.assertIsNone(briefing.important(frozenset({normalize("Rete lenta 1 ms"), normalize("Disco al 1%")})))
        with mock.patch.object(briefing.store, "events", [{"level": "ERROR", "msg": "Servizio fermo", "ts": now}]):
            self.assertEqual(briefing.important()[2], 70)


class ContextTest(unittest.TestCase):
    def test_morning_prefers_weather_and_night_security(self):
        self.assertGreater(context.boost("weather", datetime(2026, 11, 23, 7)), context.boost("firewall", datetime(2026, 11, 23, 7)))
        self.assertGreater(context.boost("firewall", datetime(2026, 11, 23, 2)), 0)

    def test_repeated_urgent_card_is_demoted(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        sec = secretary.Secretary.__new__(secretary.Secretary)
        sec.recall = Recall(Path(tmp.name) / "r.json")
        card = ("brief", {"lines": ["Servizio X giù"]}, 88)
        self.assertEqual(sec._demote("systems", card)[2], 88)
        sec.recall.mark("systems", signature("brief", card[1], True))
        self.assertEqual(sec._demote("systems", card)[2], secretary.REPEAT_PRIORITY)


if __name__ == "__main__":
    unittest.main()
