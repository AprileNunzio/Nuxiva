import time
import unittest
from unittest import mock

from agenti.medico.vitals import camera as camera_module
from agenti.medico.vitals.camera import CameraVitals
from agenti.medico.vitals.live import Live


def person(slug: str, reading: dict | None = None, known: bool = True) -> dict:
    return {"slug": slug, "known": known, "vitals": reading}


class CameraVitalsTest(unittest.TestCase):

    def setUp(self):
        self.live = Live()
        self.devices: dict[str, list] = {}
        self.env = {"NUXIVA_RPPG": "1"}
        self.denied: set = set()
        patches = (mock.patch.object(camera_module, "live", self.live),
                   mock.patch.object(camera_module.book, "of", side_effect=lambda slug: self.devices.get(slug, [])),
                   mock.patch.object(camera_module, "env_get", side_effect=lambda key, default="": self.env.get(key, default)),
                   mock.patch.object(camera_module, "server_busy", return_value=False),
                   mock.patch.object(camera_module.consent, "allowed", side_effect=lambda slug, now=None: slug not in self.denied))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.cam = CameraVitals()

    def test_privacy_of_each_person_blocks_the_measure(self):
        self.denied.add("luca")
        visible = [person("anna"), person("luca")]
        self.assertEqual(self.cam.targets(visible, 100.0), ["anna"])
        self.cam.force("luca", 30, 100.0)
        self.assertEqual(self.cam.targets(visible, 101.0), ["anna"])
        self.assertEqual(self.cam.status("luca", 101.0)["state"], "denied")

    def test_only_people_without_a_band_are_measured(self):
        self.devices["luca"] = [{"id": "a1", "kind": "ble", "enabled": True}]
        self.devices["sara"] = [{"id": "a2", "kind": "ble", "enabled": False}]
        visible = [person("anna"), person("luca"), person("sara"), person("x", known=False), person("anna")]
        self.assertEqual(self.cam.targets(visible, 100.0), ["anna", "sara"])

    def test_fresh_heart_rate_from_another_source_counts_as_a_band(self):
        now = time.time()
        self.live.put("anna", {"metric": "heart_rate", "value": 70, "ts": now - 10}, "google", "cloud", now)
        self.assertEqual(self.cam.targets([person("anna")], now), [])

    def test_owner_switch_and_busy_server_stop_the_measure(self):
        self.env["NUXIVA_RPPG"] = "0"
        self.assertEqual(self.cam.targets([person("anna")], 100.0), [])
        self.assertEqual(self.cam.status("anna", 100.0)["state"], "off")
        self.env["NUXIVA_RPPG"] = "1"
        with mock.patch.object(camera_module, "server_busy", return_value=True):
            self.assertEqual(self.cam.targets([person("anna")], 100.0), [])
            self.assertEqual(self.cam.status("anna", 100.0)["state"], "busy")

    def test_readings_are_ingested_once_and_validated(self):
        from agenti.medico.vitals import service
        now = time.time()
        good = {"heart_rate": 68, "resp_rate": 14, "hr_quality": 0.7, "rr_quality": 0.8, "progress": 1.0, "at": now}
        with mock.patch.object(service, "ingest", return_value={"accepted": 2, "rejected": 0}) as ingest:
            self.assertEqual(self.cam.ingest([person("anna", good)], None, ["anna"], now), 2)
            sent = ingest.call_args.args
            self.assertEqual(sent[0], "anna")
            self.assertEqual({s["metric"] for s in sent[1]}, {"heart_rate", "resp_rate"})
            self.assertEqual(sent[2:4], ("webcam", "camera"))
            self.cam.ingest([person("anna", {**good, "at": now + 0.5})], None, ["anna"], now + 0.5)
            self.assertEqual(ingest.call_count, 1)
            self.cam.ingest([person("anna", {**good, "at": now - 60})], None, ["anna"], now + 20)
            self.cam.ingest([person("anna", {**good, "heart_rate": 400, "resp_rate": True, "at": now + 21})], None, ["anna"], now + 21)
            self.cam.ingest([person("bruno", good)], None, ["anna"], now)
            self.assertEqual(ingest.call_count, 1)
        self.assertEqual(self.cam.status("anna", now + 21)["state"], "measuring")

    def test_cost_is_recorded_as_a_delta(self):
        from agenti.governor.service import governor
        with mock.patch.object(governor, "enabled", return_value=True), mock.patch.object(governor.ledger, "record") as record:
            self.cam.ingest([], {"cpu_ms": 50.0, "frames": 10}, ["anna"])
            self.cam.ingest([], {"cpu_ms": 80.0, "frames": 16}, ["anna"])
            self.cam.ingest([], {"cpu_ms": "x", "frames": 16}, ["anna"])
        self.assertEqual(record.call_args_list[-1].args, ("vision:rppg", "realtime", 30.0, 30.0, 6))
        self.assertEqual(record.call_count, 2)


if __name__ == "__main__":
    unittest.main()
