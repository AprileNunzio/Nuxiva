import asyncio
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from agenti.desktop import moves, surfaces as surfaces_module, surfaces_api
from agenti.desktop.moves import MoveGuard
from agenti.desktop.screens import Screens
from agenti.desktop.surfaces import Surfaces, clean_pose, clean_surface, slug


def _native(name):
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, name, None)


class Clock:

    def __init__(self, t: float = 1_800_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class Classic(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.root = Path(tempfile.mkdtemp())
        file_patch = mock.patch.object(surfaces_module, "FILE", self.root / "display" / "surfaces.json")
        file_patch.start()
        self.addCleanup(file_patch.stop)


class Request:

    def __init__(self, body) -> None:
        self.raw = json.dumps(body).encode()

    async def body(self):
        return self.raw

    async def json(self):
        return json.loads(self.raw)


class CleaningTests(unittest.TestCase):

    def test_rooms_become_safe_slugs(self):
        self.assertEqual(slug("Soggiorno Grande"), "soggiorno_grande")
        self.assertEqual(slug("Cucina!"), "cucina")
        self.assertEqual(slug("<script>"), "script")

    def test_poses_are_clamped_and_rejected_when_roomless(self):
        pose = clean_pose({"room": "Studio", "x_m": "1e9", "y_m": float("nan"), "yaw_deg": 9999})
        self.assertEqual(pose, {"room": "studio", "x_m": 100.0, "y_m": 0.0, "z_m": 0.0, "yaw_deg": 360.0})
        self.assertIsNone(clean_pose({"room": "!!!"}))
        self.assertIsNone(clean_pose("studio"))

    def test_surface_descriptors_are_whitelisted(self):
        clean = clean_surface({"kind": "rocket", "width": -5, "input": {"touch": "yes", "hands": True}, "evil": 1})
        self.assertEqual(clean["kind"], "monitor")
        self.assertEqual(clean["width"], 1)
        self.assertEqual(clean["input"], {"touch": False, "pointer": False, "hands": True, "gaze": False, "keyboard": False})
        self.assertNotIn("evil", clean)


class StorageTests(Classic):

    def test_poses_are_saved_privately_and_reloaded(self):
        store = Surfaces()
        store.save({"0": {"room": "Living", "x_m": 0}, "1": {"room": "living", "x_m": 2}, "2": None})
        path = surfaces_module.FILE
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(sorted(Surfaces().poses()), [0, 1])

    def test_invalid_configurations_are_refused(self):
        store = Surfaces()
        for body in ({"99": {"room": "a"}}, {"x": {"room": "a"}}, {"0": {"room": "!!"}}, ["0"]):
            with self.assertRaises(ValueError):
                store.save(body)

    def test_unreadable_file_falls_back_to_order(self):
        surfaces_module.FILE.parent.mkdir(parents=True)
        surfaces_module.FILE.write_text("{broken", encoding="utf-8")
        with self.assertLogs("nuxiva.desktop.surfaces", "ERROR"):
            self.assertEqual(Surfaces().poses(), {})


class LayoutTests(Classic):

    def test_classic_layout_orders_by_x(self):
        active = [{"n": 0, "x": 0}, {"n": 2, "x": 100}, {"n": 1, "x": 200}]
        out = Surfaces().annotate(active)
        self.assertEqual(out[1]["neighbors"], {"left": 0, "right": 1, "up": None, "down": None})
        self.assertEqual(out[0]["kind"], "monitor")

    def test_rooms_are_reported(self):
        store = Surfaces()
        store.save({"1": {"room": "kitchen"}})
        out = store.annotate([{"n": 0, "x": 0}, {"n": 1, "x": 10}])
        self.assertEqual([s["room"] for s in out], [None, "kitchen"])


class AudienceTests(Classic):

    def test_rooms_without_cameras_follow_strictness(self):
        store = Surfaces()
        store.save({"0": {"room": "living"}, "1": {"room": "garage"}})
        with mock.patch.object(store, "sensed_rooms", return_value=["living"]):
            with mock.patch.object(surfaces_module, "strict", return_value=False):
                self.assertEqual(store.audience_for(1, "authorized"), "authorized")
            with mock.patch.object(surfaces_module, "strict", return_value=True):
                self.assertEqual(store.audience_for(0, "authorized"), "authorized")
                self.assertEqual(store.audience_for(1, "authorized"), "uncertain")
                self.assertEqual(store.audience_for(5, "mixed"), "mixed")
        self.assertEqual(store.audience_for(5, "bogus"), "uncertain")


class MoveTests(Classic):

    def test_planner_moves_are_held_but_user_moves_pass(self):
        clock = Clock()
        guard = MoveGuard(clock=clock)
        self.assertEqual(guard.engine, "classic")
        self.assertEqual(guard.decide("clock", 1, "planner", [0, 1, 2]), 1)
        clock.t += 5
        self.assertEqual(guard.decide("clock", 2, "planner", [0, 1, 2]), 1)
        self.assertEqual(guard.decide("clock", 2, "planner", [0, 2]), 2)
        self.assertEqual(guard.decide("clock", 0, "user", [0, 2]), 0)
        clock.t += 31
        self.assertEqual(guard.decide("clock", 2, "planner", [0, 2]), 2)
        with self.assertRaises(ValueError):
            guard.decide("clock", 0, "robot", [0])

    def test_assign_does_not_bounce_widgets(self):
        manager = Screens()
        manager.guard = MoveGuard(clock=Clock())
        with mock.patch.object(manager, "numbers", return_value=[0, 1, 2]), mock.patch.object(manager, "active", return_value=[]):
            first = manager.assign([{"id": "a", "key": "a"}], {})
            placed = first[0]["screen"]
            again = manager.assign([{"id": "b", "key": "b"}, {"id": "a", "key": "a"}], {})
        self.assertEqual(next(i for i in again if i["key"] == "a")["screen"], placed)

    def test_tracked_moves_are_bounded(self):
        guard = moves._ClassicGuard(1000)
        for n in range(moves.MAX_TRACKED + 5):
            guard.decide(f"k{n}", 0, "planner", n, [0])
        self.assertEqual(len(guard.placed), moves.MAX_TRACKED)


class ApiTests(Classic):

    def test_admin_can_place_screens(self):
        with mock.patch.object(surfaces_api, "MAX_BODY", 4096):
            result = asyncio.run(surfaces_api.display_surfaces_save(Request({"poses": {"0": {"room": "Sala"}}}), "admin"))
        self.assertEqual(result["poses"]["0"]["room"], "sala")
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(surfaces_api.display_surfaces_save(Request({"poses": {"0": {"room": "!!"}}}), "admin"))
        self.assertEqual(caught.exception.status_code, 422)

    def test_oversized_bodies_are_refused(self):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(surfaces_api.display_surfaces_save(Request({"poses": {"0": {"room": "a" * 20000}}}), "admin"))
        self.assertEqual(caught.exception.status_code, 413)


@unittest.skipIf(_native("surface_layout") is None, "nuxiva_native senza motore superfici")
class NativeTests(unittest.TestCase):

    def test_physical_neighbors(self):
        layout = _native("surface_layout")
        screens = [{"n": 0, "x": 500, "surface": {"placement": {"room": "living", "x_m": 0, "y_m": 0, "z_m": 1}}},
                   {"n": 1, "x": 0, "surface": {"placement": {"room": "living", "x_m": 1.5, "y_m": 0, "z_m": 1}}},
                   {"n": 2, "x": 1000, "surface": {"placement": {"room": "living", "x_m": 0, "y_m": 0, "z_m": 2.2}}}]
        out = json.loads(layout(json.dumps(screens)))
        self.assertEqual(out["0"]["right"], 1)
        self.assertEqual(out["0"]["up"], 2)
        self.assertEqual(out["1"]["left"], 0)

    def test_native_guard_matches_classic(self):
        native = _native("RustMoveGuard")(30_000)
        classic = moves._ClassicGuard(30_000)
        steps = [("a", 1, "planner", 0, [0, 1]), ("a", 0, "planner", 10, [0, 1]), ("a", 0, "user", 20, [0, 1]),
                 ("a", 1, "planner", 40_000, [0, 1]), ("b", 2, "planner", 50, [0, 2])]
        for step in steps:
            self.assertEqual(native.decide(*step), classic.decide(*step))

    def test_native_room_audience(self):
        audience = _native("surface_audience")
        payload = json.dumps({"global": "authorized", "rooms": {}, "sensed": [], "strict": True})
        self.assertEqual(json.loads(audience(payload, "garage")), "uncertain")
        self.assertEqual(json.loads(audience(payload, None)), "authorized")
        with self.assertRaises(ValueError):
            audience(json.dumps({"global": "nope"}), None)

    def test_annotate_uses_physical_placement(self):
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(surfaces_module, "FILE", root / "surfaces.json"):
            store = Surfaces()
            store.save({"0": {"room": "living", "x_m": 2}, "1": {"room": "living", "x_m": 0}})
            out = store.annotate([{"n": 0, "x": 0, "surface": {"width": 3840, "height": 2160}}, {"n": 1, "x": 10}])
        self.assertEqual(out[0]["neighbors"]["left"], 1)
        self.assertIsNone(out[0]["neighbors"]["right"])
        self.assertNotIn("surface", out[0])
