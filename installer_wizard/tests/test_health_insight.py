import struct
import tempfile
import unittest
from pathlib import Path

from sealed import SealedFile

from agenti.medico.vitals import ble_codec, insight
from agenti.medico.vitals.history import History
from agenti.medico.vitals.model import clean_sample


def sfloat(value: int, exponent: int = 0) -> bytes:
    return struct.pack("<H", ((exponent & 0xF) << 12) | (value & 0x0FFF))


class CodecTest(unittest.TestCase):
    def test_rr_intervals_are_read_after_energy_field(self):
        data = bytes([0x18, 60]) + struct.pack("<H", 500) + struct.pack("<HH", 1024, 1000)
        self.assertEqual(ble_codec.rr_intervals(data), [1000.0, 976.6])
        self.assertEqual(ble_codec.parse_heart_rate(data), [("heart_rate", 60)])

    def test_rmssd_needs_enough_beats_and_skips_artifacts(self):
        window = ble_codec.RrWindow()
        self.assertIsNone(window.add([800.0, 810.0] * 5))
        value = window.add([800.0, 810.0] * 5 + [3000.0])
        self.assertEqual(value, 10.0)

    def test_blood_pressure_in_kpa_and_pulse(self):
        data = bytes([0x05]) + sfloat(16) + sfloat(10) + sfloat(13) + sfloat(70)
        self.assertEqual(ble_codec.parse_blood_pressure(data), [("bp_sys", 120), ("bp_dia", 75), ("heart_rate", 70)])

    def test_weight_scale_in_si_and_imperial(self):
        self.assertEqual(ble_codec.parse_weight(bytes([0]) + struct.pack("<H", 14500)), [("weight", 72.5)])
        self.assertEqual(ble_codec.parse_weight(bytes([1]) + struct.pack("<H", 16000)), [("weight", 72.6)])
        self.assertEqual(ble_codec.parse_weight(bytes([0]) + struct.pack("<H", 0xFFFF)), [])


class ModelTest(unittest.TestCase):
    def test_each_metric_has_its_own_age_limit(self):
        now = 10_000_000.0
        self.assertEqual(clean_sample({"metric": "weight", "value": 70, "ts": now - 20 * 86400}, now)["value"], 70.0)
        with self.assertRaises(ValueError):
            clean_sample({"metric": "heart_rate", "value": 70, "ts": now - 7200}, now)
        with self.assertRaises(ValueError):
            clean_sample({"metric": "steps", "value": True, "ts": now}, now)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.history = History(SealedFile(root / "h.vault", root / "h.key"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_history_is_encrypted_and_survives_a_restart(self):
        now = 1_800_000_000.0
        self.history.record("anna", {"metric": "weight", "value": 71.2, "ts": now}, "scale", "ble", now)
        self.history.flush(now, force=True)
        raw = (Path(self.tmp.name) / "h.vault").read_bytes()
        self.assertNotIn(b"weight", raw)
        again = History(SealedFile(Path(self.tmp.name) / "h.vault", Path(self.tmp.name) / "h.key"))
        self.assertEqual(again.last_known("anna", now + 60)["weight"]["value"], 71.2)

    def test_recovery_uses_personal_baseline(self):
        now = 1_800_000_000.0
        for back in range(1, 8):
            ts = now - back * 86400
            self.history.record("anna", {"metric": "hrv", "value": 50, "ts": ts}, "x", "phone", ts)
            self.history.record("anna", {"metric": "resting_hr", "value": 60, "ts": ts}, "x", "phone", ts)
        original = insight.history
        insight.history = self.history
        try:
            good = insight.recovery("anna", {"hrv": {"value": 60}, "resting_hr": {"value": 57}, "sleep_min": {"value": 480}}, now)
            poor = insight.recovery("anna", {"hrv": {"value": 35}, "resting_hr": {"value": 68}, "sleep_min": {"value": 240}}, now)
        finally:
            insight.history = original
        self.assertEqual(good["band"], "high")
        self.assertEqual(poor["band"], "low")
        self.assertIsNone(insight.recovery("nessuno", {}, now))

    def test_signals_flag_the_worst_reading_first(self):
        rows = insight.signals({"spo2": {"value": 86}, "body_temp": {"value": 38.1}, "heart_rate": {"value": 72}})
        self.assertEqual(rows[0], {"metric": "spo2", "code": "very_low", "level": "alert"})
        self.assertIn({"metric": "body_temp", "code": "fever", "level": "warn"}, rows)
        self.assertEqual(len([r for r in rows if r["metric"] == "spo2"]), 1)


class GoogleDailyTest(unittest.TestCase):
    def test_steps_sleep_and_resting_heart_rate_are_read(self):
        from datetime import datetime
        from agenti.medico.vitals import cloud
        now = datetime(2027, 1, 15, 18, 0).timestamp()
        iso = lambda h: datetime(2027, 1, 15, h, 0).astimezone().isoformat()
        steps = {"dataPoints": [{"steps": {"count": "1200", "interval": {"startTime": iso(9)}}},
                                {"steps": {"count": 800, "interval": {"startTime": iso(10)}}},
                                {"steps": {"count": "x", "interval": {"startTime": iso(11)}}}]}
        self.assertEqual(cloud.steps_today(steps, now)[0]["value"], 2000)
        sleep = {"dataPoints": [{"sleep": {"interval": {"endTime": iso(7)}, "summary": {"minutesAsleep": "421",
                 "stagesSummary": [{"type": "DEEP", "minutes": "80"}, {"type": "REM", "minutes": 95}, {"type": "LIGHT", "minutes": 246}]}}}]}
        rows = {r["metric"]: r["value"] for r in cloud.last_sleep(sleep, now)}
        self.assertEqual(rows, {"sleep_min": 421, "sleep_deep_min": 80, "sleep_rem_min": 95})
        rest = {"dataPoints": [{"dailyRestingHeartRate": {"date": {"year": 2027, "month": 1, "day": 15}, "beatsPerMinute": "58"}}]}
        self.assertEqual(cloud.resting_today(rest, now)[0]["value"], 58)
        self.assertEqual(cloud.steps_today({}, now), [])


if __name__ == "__main__":
    unittest.main()
