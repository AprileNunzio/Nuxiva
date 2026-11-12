import unittest
from unittest import mock

from agenti.medico.vitals import checkup as checkup_module
from agenti.medico.vitals import consent as consent_module
from agenti.medico.vitals.camera import CameraVitals
from agenti.medico.vitals.checkup import Watch
from agenti.medico.vitals.live import Live
from agenti.medico.vitals.watch_engine import ATTEMPT, REFRESH, SHOW, PyWatch


def engines():
    out = [PyWatch]
    try:
        import nuxiva_native
    except ImportError:
        return out
    native = getattr(nuxiva_native, "RustVitalWatch", None)
    return out + ([native] if native else [])


def person(slug: str, known: bool = True) -> dict:
    return {"slug": slug, "known": known}


class BackgroundWatchBase:
    ENGINE = PyWatch

    def setUp(self):
        self.live = Live()
        self.camera = CameraVitals()
        self.readings: dict[str, dict] = {}
        self.enabled = True
        self.denied: set = set()
        patches = (mock.patch.object(checkup_module, "live", self.live),
                   mock.patch.object(checkup_module, "camera", self.camera),
                   mock.patch.object(self.camera, "reading", side_effect=lambda slug, now=None: self.readings.get(slug)),
                   mock.patch.object(checkup_module.camera_module, "enabled", side_effect=lambda: self.enabled),
                   mock.patch.object(checkup_module.consent, "allowed", side_effect=lambda slug, now=None: slug not in self.denied))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.watch = Watch(self.ENGINE())

    def test_measure_is_silent_until_a_reliable_value_arrives(self):
        watch = self.watch
        self.assertEqual(watch.tick([person("anna")], 100.0), [])
        self.assertTrue(self.camera.forced("anna", 101.0))
        self.readings["anna"] = {"values": {}}
        self.assertEqual(watch.tick([person("anna")], 130.0), [])
        self.readings["anna"] = {"values": {"heart_rate": 71, "resp_rate": 14}}
        rows = watch.tick([person("anna")], 131.0)
        self.assertEqual([(r["slug"], r["values"], r["source"]) for r in rows], [("anna", {"heart_rate": 71, "resp_rate": 14}, "camera")])
        self.assertEqual(watch.tick([person("anna")], 131.0 + SHOW), [])
        self.assertFalse(self.camera.forced("anna", 131.0 + SHOW + 1))
        self.assertEqual(watch.tick([person("anna")], 131.0 + SHOW + REFRESH / 2), [])

    def test_failure_shows_nothing_and_retries_alone(self):
        watch = self.watch
        watch.tick([person("anna")], 1.0)
        self.assertEqual(watch.tick([person("anna")], ATTEMPT + 1.0), [])
        self.assertFalse(self.camera.forced("anna", ATTEMPT + 2.0))
        self.assertEqual(watch.tick([person("anna")], ATTEMPT + 26.0), [])
        self.assertTrue(self.camera.forced("anna", ATTEMPT + 27.0))

    def test_device_value_is_shown_without_the_camera(self):
        watch = self.watch
        self.live.put("anna", {"metric": "heart_rate", "value": 64, "ts": 99.0}, "fascia@n1", "ble", 99.0)
        rows = watch.tick([person("anna")], 100.0)
        self.assertEqual([(r["values"]["heart_rate"], r["source"]) for r in rows], [(64, "device")])
        self.assertFalse(self.camera.forced("anna", 100.5))
        self.live.forget("anna")

    def test_several_people_get_one_value_each_and_privacy_is_respected(self):
        watch = self.watch
        self.denied = {"luca"}
        crowd = [person("anna"), person("luca"), person("sara"), person("x", known=False)]
        watch.tick(crowd, 100.0)
        self.assertTrue(self.camera.forced("sara", 101.0))
        self.assertFalse(self.camera.forced("luca", 101.0))
        self.readings = {"anna": {"values": {"heart_rate": 80}}, "sara": {"values": {"heart_rate": 66}}, "luca": {"values": {"heart_rate": 90}}}
        rows = watch.tick(crowd, 110.0)
        self.assertEqual([(r["slug"], r["values"]["heart_rate"]) for r in rows], [("anna", 80), ("sara", 66)])
        self.denied = set()

    def test_leaving_stops_the_camera(self):
        watch = self.watch
        watch.tick([person("anna")], 100.0)
        watch.tick([], 105.0)
        self.assertTrue(self.camera.forced("anna", 105.5))
        watch.tick([], 110.0)
        self.assertFalse(self.camera.forced("anna", 110.5))

    def test_camera_switched_off_never_forces(self):
        watch = self.watch
        self.enabled = False
        self.assertEqual(watch.tick([person("anna")], 100.0), [])
        self.assertFalse(self.camera.forced("anna", 100.5))
        self.enabled = True


class PythonWatchTest(BackgroundWatchBase, unittest.TestCase):
    ENGINE = PyWatch


@unittest.skipUnless(len(engines()) > 1, "nuxiva_native senza RustVitalWatch")
class RustWatchTest(BackgroundWatchBase, unittest.TestCase):
    ENGINE = engines()[-1]


class ConsentTest(unittest.TestCase):

    def test_profile_rules(self):
        self.assertTrue(consent_module.decide({"role": "family"}))
        self.assertFalse(consent_module.decide({"role": "owner", "consent": False}))
        self.assertFalse(consent_module.decide({"role": "owner", "camera_vitals": False}))
        self.assertFalse(consent_module.decide({"role": "guest"}))
        self.assertTrue(consent_module.decide({"role": "guest", "share_health": True}))
        self.assertFalse(consent_module.decide(None))


class ForcedCameraTest(unittest.TestCase):

    def test_forced_people_are_measured_even_with_a_band(self):
        cam = CameraVitals()
        with mock.patch.object(cam, "has_band", return_value=True), \
                mock.patch("agenti.medico.vitals.camera.enabled", return_value=True), \
                mock.patch("agenti.medico.vitals.camera.server_busy", return_value=False), \
                mock.patch("agenti.medico.vitals.camera.consent.allowed", return_value=True):
            people = [{"slug": "anna", "known": True}]
            self.assertEqual(cam.targets(people, 100.0), [])
            cam.force("anna", 30, 100.0)
            self.assertEqual(cam.targets(people, 110.0), ["anna"])
            self.assertEqual(cam.targets(people, 131.0), [])


if __name__ == "__main__":
    unittest.main()
