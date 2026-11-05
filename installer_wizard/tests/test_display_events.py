import json
import unittest
from unittest import mock

import display_events
import snapshot
from state import store


class DisplayEventsTests(unittest.TestCase):

    def setUp(self):
        self.events = display_events.DisplayEvents()

    def test_every_client_receives_the_same_event(self):
        first = second = self.events.cursor()
        self.events.push("holo_action", {"express": "smile"})
        self.assertEqual([e.payload for e in self.events.since(first)], [{"express": "smile"}])
        self.assertEqual([e.payload for e in self.events.since(second)], [{"express": "smile"}])

    def test_events_expire(self):
        start = self.events.cursor()
        self.events.push("holo_action", {"play": "balla"}, ttl=1.0)
        self.assertEqual(self.events.since(start, now=10 ** 12), [])

    def test_pushing_wakes_the_stream(self):
        before = store.version
        self.events.push("holo_action", {"tint": "blu"})
        self.assertGreater(store.version, before)

    def test_holo_helper_drops_empty_values(self):
        with mock.patch.object(display_events, "events", self.events):
            display_events.holo({"express": "smile", "play": None, "tint": ""})
        self.assertEqual(self.events.since(0)[-1].payload, {"express": "smile"})


class SharedSnapshotTests(unittest.TestCase):

    def setUp(self):
        snapshot._shared.clear()

    def test_clients_share_one_build_per_version(self):
        with mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}) as build:
            first = snapshot.shared_snapshot(False)
            second = snapshot.shared_snapshot(False)
        self.assertEqual(build.call_count, 1)
        self.assertIs(first[1], second[1])

    def test_a_new_version_rebuilds(self):
        with mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}) as build:
            snapshot.shared_snapshot(False)
            store.touch()
            snapshot.shared_snapshot(False)
        self.assertEqual(build.call_count, 2)

    def test_two_screens_both_get_the_holographic_action(self):
        events = display_events.DisplayEvents()
        with mock.patch.object(display_events, "events", events), \
                mock.patch.object(snapshot, "full_snapshot", return_value={"v": 1}):
            screen_a = screen_b = events.cursor()
            events.push("holo_action", {"express": "smile"})
            text_a, screen_a = snapshot.frame(False, screen_a)
            text_b, screen_b = snapshot.frame(False, screen_b)
            again, _ = snapshot.frame(False, screen_a)
        self.assertEqual(json.loads(text_a)["holo_action"], {"express": "smile"})
        self.assertEqual(json.loads(text_b)["holo_action"], {"express": "smile"})
        self.assertNotIn("holo_action", json.loads(again))


if __name__ == "__main__":
    unittest.main()
