import json
import unittest
from unittest import mock

from agenti.desktop import planner_bridge
from agenti.desktop.planner_bridge import PlannerBridge, candidate
from state import store

ITEMS = [
    {"key": "weather", "id": "weather", "priority": 50, "size": "l", "screen": 0, "shown_at": 1000.0},
    {"key": "music", "id": "music", "priority": 60, "size": "m", "screen": 0, "shown_at": 1000.0},
    {"key": "health", "id": "health_hub", "priority": 70, "size": "m", "screen": 0, "personal": True, "shown_at": 1000.0},
    {"key": "alarm", "id": "alarm", "priority": 95, "size": "s", "screen": -1, "urgent": True, "shown_at": 1000.0},
]


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "display_plan", None)


class CandidateTests(unittest.TestCase):

    def test_desk_items_become_planner_candidates(self):
        c = candidate({"key": "bind:x", "id": "tv_player", "priority": 300, "takeover": True, "urgent": True,
                       "personal": True, "weight": "nope", "shown_at": 990.0, "expires_at": 1090.0}, 1000.0)
        self.assertEqual((c["importance"], c["urgency"], c["size"], c["sensitivity"]), (100, 3, "full", "personal"))
        self.assertTrue(c["forced"])
        self.assertEqual((c["cost"], c["age_ms"], c["ttl_ms"]), (1.0, 10000, 100000))
        self.assertEqual((c["media"], c["exclusive"]), ("audio", "video"))
        self.assertEqual(candidate({"key": "k", "id": "clock", "size": "weird"}, 5.0)["size"], "m")


class FakeEngineTests(unittest.TestCase):

    def fake(self, payload):
        data = json.loads(payload)
        keys = [c["key"] for c in data["candidates"] if c["key"] != "health"]
        return json.dumps({"screen": data["screen"]["id"], "rows": 7, "cap": 4,
                           "nucleus": {"form": "floating_orb", "slot": None},
                           "shown": [{"key": k, "slot": {"col": 0, "row": 0, "w": 3, "h": 2}, "muted": k == "music",
                                      "since_ms": 5} for k in keys],
                           "explain": [{"key": "health", "shown": False, "reason": "privacy", "score": 1.0, "parts": {}}]})

    def test_without_the_native_engine_the_classic_layout_stays(self):
        snap = {"desk": [dict(i) for i in ITEMS]}
        with mock.patch.object(planner_bridge, "_native", return_value=None):
            self.assertIs(PlannerBridge().apply(snap, {"kind": "authorized"}), snap)

    def test_the_plan_filters_and_annotates_the_desk(self):
        bridge = PlannerBridge()
        with mock.patch.object(planner_bridge, "_native", return_value=self.fake), \
                mock.patch.object(planner_bridge, "enabled", return_value=True):
            out = bridge.apply({"desk": [dict(i) for i in ITEMS]}, {"kind": "mixed"})
        self.assertEqual([i["key"] for i in out["desk"]], ["weather", "music", "alarm"])
        self.assertTrue(all(i["planned"] for i in out["desk"]))
        self.assertTrue(next(i for i in out["desk"] if i["key"] == "music")["muted"])
        self.assertEqual(out["scene"]["0"]["nucleus"], "floating_orb")
        self.assertIn("weather", bridge.previous[0])
        self.assertEqual(bridge.explain()["screens"]["0"]["explain"][0]["reason"], "privacy")

    def test_engine_errors_fall_back_to_the_classic_layout(self):
        def broken(_):
            raise ValueError("bad")
        snap = {"desk": [dict(i) for i in ITEMS]}
        with mock.patch.object(planner_bridge, "_native", return_value=broken), \
                mock.patch.object(planner_bridge, "enabled", return_value=True), \
                self.assertLogs("nuxiva.desktop.planner", "ERROR"):
            self.assertIs(PlannerBridge().apply(snap, {"kind": "authorized"}), snap)


@unittest.skipUnless(_native(), "motore nativo non installato")
class NativePlannerTests(unittest.TestCase):

    def setUp(self):
        self.saved = store.live_dialogue

    def tearDown(self):
        store.live_dialogue = self.saved

    def test_a_guest_never_gets_a_personal_widget_from_the_planner(self):
        with mock.patch.object(planner_bridge, "enabled", return_value=True):
            out = PlannerBridge().apply({"desk": [dict(i) for i in ITEMS]}, {"kind": "mixed"})
        keys = {i["key"] for i in out["desk"]}
        self.assertNotIn("health", keys)
        self.assertIn("alarm", keys)
        self.assertIn(out["scene"]["0"]["nucleus"], ("core_hero", "floating_orb", "ambient_stream", "whisper_pill"))

    def test_a_plan_for_four_screens_and_a_hundred_candidates_is_fast(self):
        import time
        items = [{"key": f"k{n}", "id": "weather", "priority": n % 100, "size": "s", "screen": n % 4, "shown_at": 1.0}
                 for n in range(100)]
        bridge = PlannerBridge()
        with mock.patch.object(planner_bridge, "enabled", return_value=True):
            bridge.apply({"desk": items}, {"kind": "authorized"})
            started = time.perf_counter()
            for _ in range(20):
                bridge.apply({"desk": items}, {"kind": "authorized"})
            elapsed = (time.perf_counter() - started) / 20
        self.assertLess(elapsed, 0.05)


if __name__ == "__main__":
    unittest.main()
