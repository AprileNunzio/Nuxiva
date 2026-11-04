import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.camsense import api as camsense_api
from features.camsense import imaging, service, store as store_module, tools
from features.camsense.model import SenseError


def run(coro):
    return asyncio.run(coro)


def picture(kind: str) -> bytes:
    image = np.full((120, 160, 3), 40, np.uint8)
    if kind == "open":
        cv2.rectangle(image, (20, 20), (140, 100), (30, 200, 30), -1)
        cv2.line(image, (20, 20), (140, 100), (255, 255, 255), 6)
    elif kind == "closed":
        cv2.rectangle(image, (20, 20), (140, 100), (30, 30, 210), -1)
        cv2.circle(image, (80, 60), 25, (0, 0, 0), -1)
    elif kind == "other":
        image[:] = (200, 160, 40)
        cv2.circle(image, (30, 30), 10, (255, 255, 255), -1)
    ok, data = cv2.imencode(".jpg", image)
    return data.tobytes()


class Base(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.current = "open"
        patches = [mock.patch.object(store_module, "FILE", Path(folder.name) / "camsense.json"),
                   mock.patch.object(service, "frame", self.fake_frame),
                   mock.patch("features.cameras.live.find", lambda camera: {"id": camera} if camera == "cam1" else None),
                   mock.patch("features.cameras.events.add"), mock.patch.object(service.system_store, "event")]
        self.events = patches[3].start()
        for patch in patches[:3] + patches[4:]:
            patch.start()
        self.addCleanup(mock.patch.stopall)

    async def fake_frame(self, camera):
        if self.current is None:
            raise SenseError("frame_unavailable", 502)
        return picture(self.current)

    def trained(self, name="porta"):
        service.create(name, "cam1", [0.1, 0.1, 0.8, 0.8])
        for state in ("open", "closed", "open", "closed"):
            self.current = state
            run(service.learn(name, state))
        return name


class ServiceTests(Base):

    def test_state_is_recognised_and_announced_once(self):
        name = self.trained()
        self.current = "open"
        row = run(service.check(name))
        self.assertEqual(row["state"], "open")
        self.assertEqual(self.events.call_count, 1)
        run(service.check(name))
        self.assertEqual(self.events.call_count, 1)

    def test_a_change_needs_several_consistent_readings(self):
        name = self.trained()
        self.current = "open"
        run(service.check(name))
        self.current = "closed"
        for _ in range(service.CONFIRM - 1):
            self.assertEqual(run(service.check(name))["state"], "open")
        self.assertEqual(run(service.check(name))["state"], "closed")
        self.assertEqual(self.events.call_count, 2)

    def test_a_single_odd_reading_does_not_flip_the_state(self):
        name = self.trained()
        self.current = "open"
        run(service.check(name))
        self.current = "closed"
        run(service.check(name))
        self.current = "open"
        run(service.check(name))
        self.current = "closed"
        run(service.check(name))
        self.assertEqual(store_module.sensors.get(name)["state"], "open")

    def test_unknown_scene_is_refused_not_guessed(self):
        name = self.trained()
        self.current = "other"
        row = run(service.check(name))
        self.assertEqual(row["state"], "")
        self.assertEqual(row["reason"], "unlike_any_state")

    def test_quality_reports_accuracy_and_weak_states(self):
        name = self.trained()
        quality = service.view(store_module.sensors.get(name))["quality"]
        self.assertTrue(quality["ready"])
        self.assertEqual(quality["accuracy"], 1.0)
        service.create("luce", "cam1", None)
        self.current = "open"
        run(service.learn("luce", "accesa"))
        self.current = "closed"
        run(service.learn("luce", "spenta"))
        self.assertEqual(service.view(store_module.sensors.get("luce"))["quality"]["reason"], "more_examples")

    def test_identical_states_are_flagged_as_too_similar(self):
        service.create("finta", "cam1", None)
        self.current = "open"
        for label in ("a", "b", "a", "b"):
            run(service.learn("finta", label))
        self.assertEqual(service.view(store_module.sensors.get("finta"))["quality"]["reason"], "too_similar")

    def test_tick_reads_only_trained_sensors_and_flags_a_dead_camera(self):
        name = self.trained()
        service.create("vuoto", "cam1", None)
        self.current = "open"
        run(service.tick())
        self.assertEqual(store_module.sensors.get(name)["state"], "open")
        self.assertEqual(store_module.sensors.get("vuoto")["state"], "")
        self.current = None
        for _ in range(service.LOST_AFTER):
            run(service.tick())
        self.assertEqual(store_module.sensors.get(name)["reason"], "camera_offline")
        self.assertEqual(store_module.sensors.get(name)["confidence"], 0.0)

    def test_validation_and_limits(self):
        with self.assertRaises(SenseError):
            service.create("x", "cam1", None)
        with self.assertRaises(SenseError):
            service.create("porta", "cam-inesistente", None)
        service.create("porta", "cam1", None)
        with self.assertRaises(SenseError):
            service.create("porta", "cam1", None)
        with self.assertRaises(SenseError):
            run(service.learn("porta", "<script>"))
        with self.assertRaises(SenseError):
            service.create("zona", "cam1", [0.9, 0.9, 0.5, 0.5])

    def test_moving_the_region_clears_what_was_learned(self):
        name = self.trained()
        row = service.retarget(name, "", [0.0, 0.0, 0.5, 0.5])
        self.assertEqual(row["samples"], {})
        self.assertEqual(row["state"], "")

    def test_region_changes_what_is_measured(self):
        whole = imaging.vector(picture("open"), [0, 0, 1, 1])
        corner = imaging.vector(picture("open"), [0, 0, 0.1, 0.1])
        self.assertNotEqual(whole, corner)

    def test_corrupt_frames_are_rejected(self):
        for bad in (b"", b"non una immagine"):
            with self.assertRaises(SenseError):
                imaging.vector(bad, [0, 0, 1, 1])


class ToolAndApiTests(Base):

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(camsense_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)
        patcher = mock.patch.object(service, "cameras", lambda: [{"id": "cam1", "name": "Garage", "kind": "ip"}])
        patcher.start()

    def test_tools_create_learn_and_describe(self):
        run(tools.camsense_create("porta garage", "cam1", 0.1, 0.1, 0.8, 0.8))
        self.current = "open"
        run(tools.camsense_learn("porta garage", "aperta"))
        self.current = "closed"
        run(tools.camsense_learn("porta garage", "chiusa"))
        self.assertIn("porta garage", run(tools.camsense_list()))
        self.assertIn("stato sconosciuto", run(tools.camsense_list()))
        with self.assertRaises(ValueError):
            run(tools.camsense_state("inesistente"))

    def test_api_flow(self):
        r = self.client.post("/api/camsense", json={"name": "Porta", "camera": "cam1", "region": [0.1, 0.1, 0.8, 0.8]})
        self.assertEqual(r.status_code, 200, r.text)
        for state in ("open", "closed", "open", "closed"):
            self.current = state
            self.assertEqual(self.client.post("/api/camsense/porta/learn", json={"label": state}).status_code, 200)
        listing = self.client.get("/api/camsense").json()
        self.assertEqual(listing["sensors"][0]["samples"], {"open": 2, "closed": 2})
        self.current = "open"
        self.assertEqual(self.client.post("/api/camsense/porta/check").json()["state"], "open")
        self.assertEqual(self.client.get("/api/camsense/porta/preview").headers["content-type"], "image/jpeg")
        self.assertEqual(self.client.delete("/api/camsense/porta/samples/open").status_code, 200)
        self.assertEqual(self.client.delete("/api/camsense/porta").status_code, 200)

    def test_api_rejects_bad_input(self):
        self.assertEqual(self.client.post("/api/camsense", json={"name": "x", "camera": "cam1"}).status_code, 400)
        self.assertEqual(self.client.post("/api/camsense", json={"name": "Porta", "camera": "nope"}).status_code, 404)
        self.assertEqual(self.client.post("/api/camsense/../x/learn", json={}).status_code, 404)
        self.assertEqual(self.client.post("/api/camsense/INVALID!/check").status_code, 404)
        self.assertEqual(self.client.post("/api/camsense/assente/check").status_code, 404)
        self.assertEqual(self.client.post("/api/camsense", content=b"[]").status_code, 400)


if __name__ == "__main__":
    unittest.main()
