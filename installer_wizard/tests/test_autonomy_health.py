import json
import unittest

from agenti.autonomy import health


def flat(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from flat(v)
    elif isinstance(value, list):
        yield from (x for v in value for x in flat(v))
    else:
        yield value


class AutonomyHealthTest(unittest.TestCase):
    def test_snapshot_has_only_counters_flags_and_alert_codes(self):
        snap = health.snapshot()
        self.assertEqual(set(snap), {"queue", "initiative", "lessons", "alerts"})
        for section in ("queue", "initiative", "lessons"):
            self.assertIsInstance(snap[section]["available"], bool)
        for value in flat({k: snap[k] for k in ("queue", "initiative", "lessons")}):
            self.assertIsInstance(value, (int, str, bool))
        self.assertTrue(set(snap["alerts"]) <= {"queue_unavailable", "journal_errors", "events_dropped", "initiative_unavailable", "lessons_unavailable"})
        json.dumps(snap)

    def test_negative_or_non_integer_counts_become_zero(self):
        self.assertEqual(health._count(-3), 0)
        self.assertEqual(health._count("7"), 0)
        self.assertEqual(health._count(True), 0)
        self.assertEqual(health._count(5), 5)

    def test_alerts_follow_availability(self):
        down = {"available": False}
        up = {"available": True, "journal_errors": 0, "dropped_events": 0}
        self.assertEqual(health._alerts(down, down, down), ["queue_unavailable", "initiative_unavailable", "lessons_unavailable"])
        self.assertEqual(health._alerts({**up, "journal_errors": 1}, {"available": True}, {"available": True}), ["journal_errors"])


if __name__ == "__main__":
    unittest.main()
