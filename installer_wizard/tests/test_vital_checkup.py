import unittest
from unittest import mock

from features.people.vitals import checkup as checkup_module
from features.people.vitals.camera import CameraVitals
from features.people.vitals.checkup import Checkup
from features.people.vitals.live import Live


class CheckupTest(unittest.TestCase):

    def setUp(self):
        self.live = Live()
        self.devices: list = []
        self.camera = CameraVitals()
        self.reading: dict | None = None
        self.enabled = True
        patches = (mock.patch.object(checkup_module, "live", self.live),
                   mock.patch.object(checkup_module.book, "of", side_effect=lambda slug: self.devices),
                   mock.patch.object(checkup_module, "camera", self.camera),
                   mock.patch.object(self.camera, "reading", side_effect=lambda slug, now=None: self.reading),
                   mock.patch.object(checkup_module.camera_module, "enabled", side_effect=lambda: self.enabled))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.check = Checkup()

    def test_without_a_band_it_guides_a_webcam_measure(self):
        view = self.check.tick("anna", True, 100.0)
        self.assertEqual(view["phase"], "greet")
        view = self.check.tick("anna", True, 103.0)
        self.assertEqual(view["phase"], "camera")
        self.assertEqual(view["hold_left"], 20)
        self.assertTrue(self.camera.forced("anna", 104.0))
        self.reading = {"progress": 0.8, "values": {"heart_rate": 71}}
        view = self.check.tick("anna", True, 118.0)
        self.assertEqual((view["phase"], view["values"]["heart_rate"], view["hold_left"]), ("camera", 71, 5))
        self.reading = {"progress": 0.2, "values": {}}
        self.assertTrue(self.check.tick("anna", True, 119.0)["moved"])
        self.reading = {"progress": 1.0, "values": {"resp_rate": 14}}
        view = self.check.tick("anna", True, 130.0)
        self.assertEqual((view["phase"], view["source"], view["values"]), ("done", "camera", {"heart_rate": 71, "resp_rate": 14}))
        self.assertFalse(self.camera.forced("anna", 131.0))
        self.assertEqual(self.check.tick("anna", True, 150.0)["phase"], "done")
        self.assertIsNone(self.check.tick("anna", True, 160.0))
        self.assertIsNone(self.check.tick("anna", True, 1000.0))
        self.assertEqual(self.check.tick("anna", True, 130.0 + 31 * 60)["phase"], "greet")

    def test_a_linked_band_is_tried_first_then_the_webcam(self):
        self.devices = [{"label": "Fascia", "kind": "ble", "enabled": True}]
        self.check.tick("anna", True, 100.0)
        view = self.check.tick("anna", True, 103.0)
        self.assertEqual((view["phase"], view["devices"][0]["label"]), ("device", "Fascia"))
        self.assertEqual(self.check.tick("anna", True, 120.0)["phase"], "device")
        self.assertEqual(self.check.tick("anna", True, 129.0)["phase"], "camera")

    def test_band_values_finish_the_check(self):
        self.devices = [{"label": "Fascia", "kind": "ble", "enabled": True}]
        self.check.tick("anna", True, 100.0)
        self.check.tick("anna", True, 103.0)
        self.live.put("anna", {"metric": "heart_rate", "value": 64, "ts": 104.0}, "fascia@n1", "ble", 104.0)
        view = self.check.tick("anna", True, 105.0)
        self.assertEqual((view["phase"], view["source"], view["values"]["heart_rate"]), ("done", "device", 64))

    def test_leaving_stops_and_allows_a_retry_later(self):
        self.check.tick("anna", True, 100.0)
        self.check.tick("anna", True, 103.0)
        self.assertEqual(self.check.tick("anna", False, 105.0)["phase"], "camera")
        self.assertIsNone(self.check.tick("anna", False, 112.0))
        self.assertFalse(self.camera.forced("anna", 112.0))
        self.assertIsNone(self.check.tick("anna", True, 150.0))
        self.assertEqual(self.check.tick("anna", True, 175.0)["phase"], "greet")

    def test_nothing_is_shown_when_no_measure_is_possible(self):
        self.enabled = False
        self.assertIsNone(self.check.tick("anna", True, 100.0))
        self.assertIsNone(self.check.tick("anna", False, 100.0))

    def test_no_reading_ends_in_a_failure(self):
        self.check.tick("anna", True, 100.0)
        self.check.tick("anna", True, 103.0)
        self.assertEqual(self.check.tick("anna", True, 174.0)["phase"], "failed")


class ForcedCameraTest(unittest.TestCase):

    def test_forced_people_are_measured_even_with_a_band(self):
        cam = CameraVitals()
        with mock.patch.object(cam, "has_band", return_value=True), \
                mock.patch("features.people.vitals.camera.enabled", return_value=True), \
                mock.patch("features.people.vitals.camera.server_busy", return_value=False):
            people = [{"slug": "anna", "known": True}]
            self.assertEqual(cam.targets(people, 100.0), [])
            cam.force("anna", 30, 100.0)
            self.assertEqual(cam.targets(people, 110.0), ["anna"])
            self.assertEqual(cam.targets(people, 131.0), [])


if __name__ == "__main__":
    unittest.main()
