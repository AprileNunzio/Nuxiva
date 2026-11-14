import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import duplex_link


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FakeService:
    def __init__(self):
        self.nuxiva_speaking = True
        self.events = []

    async def broadcast(self, **event):
        self.events.append(event)


def run(coro):
    return asyncio.run(coro)


class DuplexLinkTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.link = duplex_link.DuplexLink(self.clock)

    def rust(self):
        return mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "rust"})

    def test_legacy_is_the_default_and_unknown_values_fall_back(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NUXIVA_DUPLEX", None)
            self.assertEqual(duplex_link.mode(), "legacy")
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "weird"}):
            self.assertEqual(duplex_link.mode(), "legacy")
        with self.rust():
            self.assertEqual(duplex_link.mode(), "rust")

    def test_legacy_mode_never_touches_the_session(self):
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "legacy"}):
            self.assertIsNone(self.link.speaking(True))
            self.assertIsNone(self.link.cut())
            self.assertIsNone(self.link.tick())
            self.assertEqual(self.link.snapshot()["state"], "idle")

    def test_speaking_walks_the_state_machine_in_rust_mode(self):
        with self.rust():
            self.assertEqual(self.link.speaking(True)["state"], "speaking")
            self.assertIsNone(self.link.speaking(True))
            self.assertEqual(self.link.speaking(False)["state"], "idle")
            self.assertIsNone(self.link.speaking(False))

    def test_cut_interrupts_and_a_new_reply_can_follow(self):
        with self.rust():
            self.link.speaking(True)
            report = self.link.cut()
            self.assertEqual(report["state"], "interrupted")
            self.assertEqual(self.link.snapshot()["state"], "interrupted")
            self.assertEqual(self.link.speaking(True)["state"], "speaking")
            self.assertEqual(self.link.snapshot()["gen"], 2)

    def test_cut_outside_speech_changes_nothing(self):
        with self.rust():
            self.assertIsNotNone(self.link.cut())
            self.assertEqual(self.link.snapshot()["state"], "idle")

    def test_timeouts_return_to_a_safe_state(self):
        with self.rust():
            self.link.speaking(True)
            self.link.cut()
            self.clock.t += 3
            self.assertEqual(self.link.tick()["state"], "listening")

    def test_manual_cut_silences_and_broadcasts_in_both_modes(self):
        for value in ("legacy", "rust"):
            with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": value}):
                link = duplex_link.DuplexLink(self.clock)
                service = FakeService()
                link.speaking(True)
                self.assertTrue(run(link.handle(service, "cut", {})))
                self.assertFalse(service.nuxiva_speaking)
                self.assertEqual(service.events[0], {"type": "barge", "reason": "manual"})
                self.assertEqual(len(service.events), 2 if value == "rust" else 1)

    def test_health_is_counters_only(self):
        with self.rust():
            self.link.speaking(True)
            self.link.cut()
            self.clock.t += 3
            self.link.tick()
            health = self.link.health()
            self.assertEqual(set(health), {"mode", "state", "generation", "bound_tokens", "replies", "cuts", "manual_cuts", "timeouts"})
            self.assertEqual((health["replies"], health["cuts"], health["timeouts"]), (1, 1, 1))
            self.assertTrue(all(isinstance(v, (int, str)) for v in health.values()))
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "legacy"}):
            self.assertEqual(duplex_link.DuplexLink(self.clock).health()["state"], "idle")

    def test_speaking_messages_publish_state_changes_and_are_not_consumed(self):
        with self.rust():
            service = FakeService()
            self.assertFalse(run(self.link.handle(service, "speaking", {"on": True})))
            self.assertEqual(service.events[-1]["type"], "duplex")
            self.assertEqual(service.events[-1]["state"], "speaking")
            self.assertFalse(run(self.link.handle(service, "listen", {})))


if __name__ == "__main__":
    unittest.main()
