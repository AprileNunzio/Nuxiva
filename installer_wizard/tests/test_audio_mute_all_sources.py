import asyncio
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.devices import audio

SOURCES = [
    {"name": "alsa_input.usb-mic", "ports": []},
    {"name": "alsa_input.usb-webcam", "ports": []},
    {"name": "alsa_output.pci.monitor", "monitor_of": "alsa_output.pci", "ports": []},
    {"name": "bad name;rm", "ports": []},
]


class MuteAllSourcesTest(unittest.TestCase):

    def run_update(self, changes):
        calls = []

        async def fake_pactl(*args):
            calls.append(args)
            return 0, ""

        async def fake_list(kind):
            return SOURCES if kind == "sources" else []

        async def fake_status():
            return {}

        with mock.patch.object(audio, "_pactl", fake_pactl), mock.patch.object(audio, "_list", fake_list), \
                mock.patch.object(audio, "status", fake_status):
            asyncio.run(audio.update(changes))
        return calls

    def test_mute_reaches_every_capture_source(self):
        calls = self.run_update({"input": {"muted": True}})
        self.assertIn(("set-source-mute", "@DEFAULT_SOURCE@", "1"), calls)
        self.assertIn(("set-source-mute", "alsa_input.usb-mic", "1"), calls)
        self.assertIn(("set-source-mute", "alsa_input.usb-webcam", "1"), calls)
        self.assertFalse(any("monitor" in " ".join(c) for c in calls))
        self.assertFalse(any("bad name;rm" in c for c in calls))

    def test_unmute_restores_every_capture_source(self):
        calls = self.run_update({"input": {"muted": False}})
        self.assertIn(("set-source-mute", "alsa_input.usb-mic", "0"), calls)
        self.assertIn(("set-source-mute", "alsa_input.usb-webcam", "0"), calls)

    def test_output_mute_leaves_sources_alone(self):
        calls = self.run_update({"output": {"muted": True}})
        self.assertEqual(calls, [("set-sink-mute", "@DEFAULT_SINK@", "1")])


if __name__ == "__main__":
    unittest.main()
