import unittest
from datetime import datetime
from unittest import mock

from agenti.desktop import extra_cards, secretary


def iso(ts):
    return datetime.fromtimestamp(ts).isoformat()


class WelcomeTest(unittest.TestCase):
    def test_short_absence_has_no_card(self):
        self.assertIsNone(extra_cards.welcome([], 1000.0, 1000.0 + 600))
        self.assertIsNone(extra_cards.welcome([], 0.0, 99999.0))

    def test_summary_counts_only_events_while_away(self):
        since, now = 1_700_000_000.0, 1_700_000_000.0 + 2 * 3600 + 300
        events = [{"ts": iso(since - 50), "level": "ERROR"}, {"ts": iso(since + 10), "level": "ERROR"},
                  {"ts": iso(since + 20), "level": "WARN"}, {"ts": iso(since + 30), "level": "WARN"}, {"ts": "bad", "level": "WARN"}]
        devices = [{"first_seen": since + 5}, {"first_seen": since - 5}]
        name, data, priority = extra_cards.welcome(events, since, now, ["Nunzio"], devices)
        self.assertEqual((name, priority), ("brief", 72))
        self.assertEqual(data["title"], {"key": "bf_away_title", "params": {}})
        self.assertEqual([(ln["key"], ln["params"]) for ln in data["lines"]],
                         [("bf_away_for", {"time": "2h 05m"}), ("bf_away_errors", {"n": "1"}), ("bf_away_alerts", {"n": "2"}),
                          ("bf_away_devices", {"n": "1"}), ("bf_away_people", {"names": "Nunzio"})])

    def test_quiet_absence(self):
        data = extra_cards.welcome([], 1000.0, 1000.0 + 3700)[1]
        self.assertEqual([ln["key"] for ln in data["lines"]], ["bf_away_for", "bf_away_quiet"])


class MeshTest(unittest.TestCase):
    def test_offline_nodes_raise_priority(self):
        nodes = [{"name": "Sala", "online": True}, {"name": "Garage", "online": False}]
        with mock.patch("agenti.nodes.registry.registry.listing", return_value=nodes):
            _, data, priority = extra_cards.mesh()
        self.assertEqual(priority, extra_cards.MESH_URGENT)
        self.assertEqual(data["lines"][1], {"key": "bf_mesh_offline", "params": {"name": "Garage"}})
        with mock.patch("agenti.nodes.registry.registry.listing", return_value=[]):
            self.assertIsNone(extra_cards.mesh())


class AwayTrackingTest(unittest.TestCase):
    def test_short_absence_is_forgotten_on_return(self):
        sec = secretary.Secretary.__new__(secretary.Secretary)
        sec.away_from, sec.back_at = 1000.0, 0.0
        with mock.patch.object(secretary.extra_cards, "welcome", return_value=None) as built, \
                mock.patch("agenti.people.panel.visible_people", return_value=[]), \
                mock.patch("agenti.people.panel.roster", return_value=[]):
            sec.back_at = 5000.0
            sec.welcome()
        self.assertEqual(built.call_args.args[1:3], (1000.0, 5000.0))


if __name__ == "__main__":
    unittest.main()
