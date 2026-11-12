import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import fastapi.routing

VISION = Path(__file__).resolve().parents[1] / "features" / "vision"


def load_observer():
    assert fastapi.routing.APIRouter
    fake_views = types.SimpleNamespace(MAX_BYTES=8 * 1024 * 1024, decode=lambda data: np.zeros((240, 320, 3), np.uint8))
    spec = importlib.util.spec_from_file_location("observer_under_test", VISION / "observer.py")
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"views": fake_views}):
        spec.loader.exec_module(module)
    return module


observer_mod = load_observer()


def face(width=120.0):
    return np.array([10.0, 10.0, width, width] + [0.0] * 11)


class FakeGallery:
    def __init__(self, known=None):
        self.known = known
        self.saved, self.added = [], []

    def match_ex(self, feature):
        return {"slug": self.known, "ambiguous": False}

    def may_learn(self, slug, feature):
        return True

    def add_samples(self, slug, rgb, ir=None):
        self.added.append((slug, len(rgb)))

    def closest(self, feature):
        return None, 0.0

    def next_guest_name(self):
        return "Ospite 1"

    def save(self, name, embeddings, photo, auto=False, slug=None, ir=None):
        self.saved.append({"name": name, "samples": len(embeddings), "auto": auto, "slug": slug})
        return {"name": name, "slug": slug}


def build(gallery, faces):
    views = SimpleNamespace(auto=mock.Mock(return_value="front"), vision=SimpleNamespace(_crop=lambda img, box: np.full((80, 80, 3), 128, np.uint8)))
    obs = observer_mod.Observer(views, gallery)
    obs._faces = lambda img: faces
    obs._sharp = lambda crop: True
    return obs, views


class ObserverTest(unittest.TestCase):
    def test_known_person_gets_views_and_samples_from_any_camera(self):
        gallery = FakeGallery(known="nunzio")
        obs, views = build(gallery, [(face(), np.ones(128))])
        result = obs.observe("c-portone", np.zeros((10, 10, 3), np.uint8))
        self.assertEqual(result["known"], ["nunzio"])
        views.auto.assert_called_once()
        self.assertEqual(gallery.added, [("nunzio", 1)])

    def test_stranger_becomes_a_guest_after_enough_consistent_sightings(self):
        gallery = FakeGallery()
        obs, _ = build(gallery, [(face(), np.ones(128))])
        for _ in range(observer_mod.SAMPLES_TO_ENROLL - 1):
            self.assertEqual(obs.observe("c-portone", np.zeros((10, 10, 3), np.uint8))["created"], [])
        result = obs.observe("c-portone", np.zeros((10, 10, 3), np.uint8))
        self.assertEqual(len(result["created"]), 1)
        self.assertTrue(gallery.saved[0]["auto"])
        self.assertTrue(gallery.saved[0]["slug"].startswith("ospite-"))
        self.assertEqual(gallery.saved[0]["samples"], observer_mod.SAMPLES_TO_ENROLL)

    def test_two_different_strangers_are_not_merged(self):
        gallery = FakeGallery()
        a, b = np.zeros(128), np.zeros(128)
        a[0], b[1] = 1.0, 1.0
        obs, _ = build(gallery, [(face(), a), (face(), b)])
        for _ in range(observer_mod.SAMPLES_TO_ENROLL):
            obs.observe("c-1", np.zeros((10, 10, 3), np.uint8))
        self.assertEqual(len(gallery.saved), 2)

    def test_stale_clusters_expire(self):
        gallery = FakeGallery()
        obs, _ = build(gallery, [(face(), np.ones(128))])
        obs.observe("c-1", np.zeros((10, 10, 3), np.uint8))
        obs._expire(10 ** 12)
        self.assertEqual(obs.pending, {})

    def test_route_rejects_unsafe_source_names(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(observer_mod.router(build(FakeGallery(), [])[0]))
        client = TestClient(app)
        self.assertEqual(client.post("/observe", params={"source": "a/b c"}, content=b"x").status_code, 400)
        self.assertEqual(client.post("/observe", params={"source": "c-1"}, content=b"").status_code, 413)
        self.assertEqual(client.post("/observe", params={"source": "c-1"}, content=b"jpeg").json()["faces"], 0)


class CameraWatchTest(unittest.TestCase):
    def test_main_webcam_and_infrared_are_left_to_the_vision_service(self):
        from features.people import camera_watch
        rows = [{"id": "w-1", "kind": "local", "main": True}, {"id": "i-1", "kind": "infrared", "main": False},
                {"id": "c-2", "kind": "ip", "main": False}, {"id": "w-3", "kind": "local", "main": False}]
        fake_live = SimpleNamespace(all_rows=lambda: rows)
        with mock.patch.dict(sys.modules, {"features.cameras.live": fake_live}), \
                mock.patch("features.cameras.live", fake_live, create=True):
            import features.cameras as cameras_pkg
            with mock.patch.object(cameras_pkg, "live", fake_live, create=True):
                self.assertEqual([r["id"] for r in camera_watch.sources()], ["c-2", "w-3"])

    def test_sightings_keep_one_row_per_camera_and_are_private(self):
        from features.people import camera_watch, private_store
        saved = {}
        profile = {"slug": "nunzio", "sightings": [{"source": "c-2", "at": 1}, {"source": "c-9", "at": 2}]}
        with mock.patch.object(camera_watch.people, "load", return_value=profile), \
                mock.patch.object(camera_watch.people, "save", side_effect=lambda p: saved.update(p)):
            camera_watch.remember(["nunzio"], {"id": "c-2", "name": "Portone", "room": "Ingresso"}, 50.0)
        self.assertEqual([s["source"] for s in saved["sightings"]], ["c-9", "c-2"])
        self.assertEqual(saved["sightings"][-1]["camera"], "Portone")
        self.assertIn("sightings", private_store.PRIVATE_KEYS)

    def test_sweep_adopts_new_guests_into_people(self):
        from features.people import camera_watch
        source = {"id": "c-2", "name": "Portone"}
        with mock.patch.object(camera_watch, "sources", return_value=[source]), \
                mock.patch.object(camera_watch, "observe", mock.AsyncMock(return_value={"known": [], "created": ["ospite-1"]})), \
                mock.patch.object(camera_watch, "adopt", mock.AsyncMock(return_value=["ospite-1"])) as adopt, \
                mock.patch.object(camera_watch, "remember") as remember:
            asyncio.run(camera_watch.sweep(None))
        adopt.assert_awaited_once()
        remember.assert_called_once_with(["ospite-1"], source, mock.ANY)


if __name__ == "__main__":
    unittest.main()
