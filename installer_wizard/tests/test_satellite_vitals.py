import importlib.util
import unittest
from pathlib import Path

SATELLITE = Path(__file__).resolve().parents[2] / "client_satellite" / "linux_edge" / "satellite.py"
spec = importlib.util.spec_from_file_location("satellite_agent", SATELLITE)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class DecoderTest(unittest.TestCase):
    def test_heart_rate_eight_and_sixteen_bit(self):
        self.assertEqual(agent.parse_heart_rate(bytes([0, 72])), [("heart_rate", 72)])
        self.assertEqual(agent.parse_heart_rate(bytes([1, 0x2C, 0x01])), [("heart_rate", 300)])

    def test_truncated_frames_are_ignored(self):
        for parser in (agent.parse_heart_rate, agent.parse_temperature, agent.parse_oximeter):
            self.assertEqual(parser(b""), [])
        self.assertEqual(agent.parse_heart_rate(bytes([1, 5])), [])
        self.assertEqual(agent.parse_temperature(bytes([0, 1, 2])), [])

    def test_temperature_celsius_and_fahrenheit(self):
        self.assertEqual(agent.parse_temperature(bytes([0, 0x6C, 0x01, 0x00, 0xFF])), [("body_temp", 36.4)])
        self.assertEqual(agent.parse_temperature(bytes([1, 0xE2, 0x03, 0x00, 0xFF])), [("body_temp", 37.4)])

    def test_temperature_nan_is_dropped(self):
        self.assertEqual(agent.parse_temperature(bytes([0, 0xFF, 0xFF, 0x7F, 0x00])), [])

    def test_oximeter_reports_oxygen_and_pulse(self):
        self.assertEqual(agent.parse_oximeter(bytes([0, 0x61, 0x00, 0x48, 0x00])), [("spo2", 97), ("heart_rate", 72)])
        self.assertEqual(agent.parse_oximeter(bytes([0, 0xFF, 0x07, 0x48, 0x00])), [("heart_rate", 72)])


if __name__ == "__main__":
    unittest.main()
