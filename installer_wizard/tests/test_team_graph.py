import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import native_core

from agenti.team import graph_view
from agenti.team.graph import MAX_LOG, GraphBridge
from agenti.team.shadow_store import ShadowStore
from agenti.team.swarm import Swarm

NATIVE = native_core.symbol("RustGraph") is not None
DAY = 86400.0


class Clock:
    def __init__(self, start=1_800_000_000.0):
        self.now = start

    def __call__(self):
        return self.now


def project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="nuxiva-graph-"))
    (root / "src").mkdir()
    (root / "src" / "lib.rs").write_text("mod util;\npub fn start() {}\n", encoding="utf-8")
    (root / "src" / "util.rs").write_text("pub fn helper() {}\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# Guida\nVedi `src/util.rs`.\n", encoding="utf-8")
    return root


class ShadowStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="nuxiva-shadow-"))
        self.path = self.dir / "team" / "swarm_shadow.json"
        self.clock = Clock()

    def store(self):
        return ShadowStore(self.path, self.clock)

    def test_counts_survive_a_restart(self):
        first = self.store()
        for same in (True, True, False, True):
            first.record(same)
        first.record(error=True)
        first.flush()
        second = self.store()
        self.assertEqual(second.totals, {"compared": 4, "matched": 3, "mismatched": 1, "errors": 1})
        self.assertEqual(second.streak, 1)

    def test_file_is_private_and_atomic(self):
        store = self.store()
        store.record(True)
        store.flush()
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertFalse(self.path.with_suffix(".tmp").exists())

    def test_corrupt_file_is_set_aside_not_trusted(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertLogs("nuxiva.team.shadow", "ERROR"):
            store = self.store()
        self.assertEqual(store.totals["compared"], 0)
        self.assertTrue(self.path.with_suffix(".bad").exists())

    def test_hostile_values_are_clamped_to_zero(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"schema": 1, "totals": {"compared": -5, "matched": "x", "mismatched": 10**30, "errors": True},
                                         "streak": -1, "days": {"2026-01-01": {"compared": "a"}, "x": 5}}), encoding="utf-8")
        store = self.store()
        self.assertEqual(store.totals, {"compared": 0, "matched": 0, "mismatched": 0, "errors": 0})
        self.assertEqual(store.streak, 0)

    def test_gate_needs_two_weeks_and_clean_days(self):
        store = self.store()
        for _ in range(16):
            store.record(True)
            self.clock.now += DAY
        gate = store.gate()
        self.assertTrue(gate["ready"])
        self.assertGreaterEqual(gate["clean_days"], 3)

    def test_gate_closes_after_a_difference(self):
        store = self.store()
        for _ in range(16):
            store.record(True)
            self.clock.now += DAY
        store.record(False)
        gate = store.gate()
        self.assertFalse(gate["ready"])
        self.assertEqual(gate["streak"], 0)
        self.assertEqual(gate["window_mismatches"], 1)

    def test_gate_is_not_ready_too_early(self):
        store = self.store()
        for _ in range(5):
            store.record(True)
        self.assertFalse(store.gate()["ready"])

    def test_old_days_are_trimmed(self):
        store = self.store()
        store.record(True)
        self.clock.now += 90 * DAY
        store.record(True)
        store.flush()
        self.assertEqual(len(self.store().days), 1)

    def test_swarm_seeds_stats_and_records_through_the_store(self):
        store = self.store()
        store.record(True)
        swarm = Swarm(store)
        self.assertEqual(swarm.stats["compared"], 1)
        swarm._error()
        self.assertEqual(store.totals["errors"], 1)
        self.assertEqual(Swarm().stats, {"compared": 0, "matched": 0, "mismatched": 0, "errors": 0})


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class GraphBridgeTest(unittest.TestCase):
    def setUp(self):
        self.bridge = GraphBridge(project())

    def test_overview_reports_the_project(self):
        data = self.bridge.overview()
        self.assertTrue(data["available"])
        self.assertEqual(data["files"], 3)
        self.assertGreaterEqual(data["symbols"], 2)

    def test_locate_neighbors_impact_and_path(self):
        found = self.bridge.explore("test", "locate", "helper")
        self.assertTrue(found["ok"])
        self.assertTrue(any(i["name"] == "helper" for i in found["items"]))
        reach = self.bridge.explore("test", "impact", "src/util.rs", 3)
        self.assertTrue(reach["ok"])
        self.assertTrue(any(i["path"] == "src/lib.rs" for i in reach["items"]))
        near = self.bridge.explore("test", "neighbors", "src/lib.rs", 1)
        self.assertTrue(near["ok"])
        route = self.bridge.explore("test", "path", "src/lib.rs", other="src/util.rs")
        self.assertTrue(route["ok"])

    def test_bad_requests_fail_closed(self):
        self.assertEqual(self.bridge.explore("t", "hack", "x")["error"], "graph.mode")
        self.assertEqual(self.bridge.explore("t", "locate", "  ")["error"], "graph.target")
        self.assertFalse(self.bridge.call("t", "run_command", {"command": "id"})["ok"])
        self.assertFalse(self.bridge.explore("t", "neighbors", "../../etc/passwd")["ok"])

    def test_consultations_are_logged_bounded_and_clipped(self):
        for index in range(MAX_LOG + 20):
            self.bridge.explore("x" * 90 + "\n", "locate", f"helper{index}")
        rows = self.bridge.consultations(500)
        self.assertEqual(len(rows), MAX_LOG)
        self.assertEqual(len(rows[0]["who"]), 40)
        self.assertNotIn("\n", rows[0]["who"])
        self.assertTrue(rows[0]["at"] >= rows[-1]["at"])
        self.assertEqual(self.bridge.consultations(3)[0]["tool"], "graph_locate")

    def test_unavailable_root_degrades_without_raising(self):
        broken = GraphBridge(Path("/nonexistent/nuxiva-root"))
        with self.assertLogs("nuxiva.team.graph", "ERROR"):
            self.assertFalse(broken.available)
        self.assertEqual(broken.call("t", "graph_sync")["error"], "graph.unavailable")
        self.assertFalse(broken.overview()["available"])


class ViewTest(unittest.TestCase):
    def test_plan_view_is_bounded_text(self):
        from agenti.team.swarm import swarm
        previous = swarm.last_plan
        self.addCleanup(setattr, swarm, "last_plan", previous)
        swarm.last_plan = {"at": 5, "task": {}, "plan": {"steps": [{"id": "1", "worker_template": "meteo\n", "intent": "x" * 500, "goal_ref": "g"}] * 40},
                           "report": {"steps": [{"step": 1, "outcome": "ok"}]}}
        view = graph_view.plan()
        self.assertEqual(len(view["steps"]), 24)
        self.assertEqual(len(view["steps"][0]["intent"]), 160)
        self.assertNotIn("\n", view["steps"][0]["agent"])
        self.assertEqual(view["steps"][0]["outcome"], "ok")
        self.assertEqual(view["done"], 1)

    def test_plan_view_without_a_plan(self):
        from agenti.team.swarm import swarm
        previous = swarm.last_plan
        self.addCleanup(setattr, swarm, "last_plan", previous)
        swarm.last_plan = None
        self.assertIsNone(graph_view.plan())
        swarm.last_plan = {"plan": "junk", "report": 3}
        self.assertEqual(graph_view.plan()["steps"], [])

    def test_shadow_view_has_counters_only(self):
        view = graph_view.shadow()
        self.assertEqual(set(view), {"totals", "gate", "persistent"})
        self.assertTrue(all(isinstance(v, int) for v in view["totals"].values()))

    def test_routes_are_admin_only(self):
        from agenti.team import api
        paths = {r.path: r for r in api.admin_routes.routes}
        for path in ("/api/team/graph", "/api/team/graph/explore"):
            self.assertIn(path, paths)
            self.assertTrue(any("require_admin" in repr(d.call) for d in paths[path].dependant.dependencies))
