import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import barge
import barge_gate
import duplex_link

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustBarge")


class FakePrints:
    ready = True

    def __init__(self, slug="anna", score=0.85, other=0.3, limit=0.6):
        self.slug, self.score, self.other, self.limit_value = slug, score, other, limit

    def embed(self, audio):
        return np.ones(4, dtype=np.float32)

    def verdict(self, probe):
        return {"slug": self.slug, "score": self.score}

    def scores(self, probe):
        return {"anna": self.score, "luca": self.other} if self.slug else {"luca": self.other}

    def limit(self, slug):
        return self.limit_value


class FakeService:
    def __init__(self, prints):
        self.voiceprints = prints
        self.nuxiva_speaking = True
        self.echo_cancelled_input = True
        self.events = []
        self.programme = False

    def _programme(self):
        return self.programme

    async def broadcast(self, **event):
        self.events.append(event)


FRAME = np.zeros(480, dtype=np.float32)


async def pump(service, windows):
    for _ in range(windows * 9):
        await barge_gate.observe(service, FRAME, True, False)


class GateTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "rust"})
        self.env.start()
        self.addCleanup(self.env.stop)
        duplex_link.link._session = None
        duplex_link.link._barge = None
        duplex_link.link.counts = {k: 0 for k in duplex_link.link.counts}
        duplex_link.link.speaking(True)

    def run_service(self, service, windows):
        asyncio.run(pump(service, windows))

    def test_the_owner_voice_cuts_after_three_strong_windows(self):
        service = FakeService(FakePrints())
        self.run_service(service, 4)
        self.assertFalse(service.nuxiva_speaking)
        self.assertEqual(service.events[0], {"type": "barge", "reason": "voice"})
        self.assertEqual(duplex_link.link.health()["voice_cuts"], 1)

    def test_two_windows_are_not_enough(self):
        service = FakeService(FakePrints())
        self.run_service(service, 2)
        self.assertTrue(service.nuxiva_speaking)

    def test_unknown_close_or_weak_voices_never_cut(self):
        for prints in (FakePrints(slug=None), FakePrints(score=0.65), FakePrints(other=0.8)):
            duplex_link.link._session = None
            duplex_link.link._barge = None
            duplex_link.link.speaking(True)
            service = FakeService(prints)
            self.run_service(service, 30)
            self.assertTrue(service.nuxiva_speaking)

    def test_programme_and_missing_echo_cancellation_never_cut(self):
        service = FakeService(FakePrints())
        service.programme = True
        self.run_service(service, 30)
        self.assertTrue(service.nuxiva_speaking)
        duplex_link.link._session = None
        duplex_link.link._barge = None
        duplex_link.link.speaking(True)
        service = FakeService(FakePrints())
        service.echo_cancelled_input = False
        self.run_service(service, 30)
        self.assertTrue(service.nuxiva_speaking)

    def test_legacy_mode_and_unready_prints_do_nothing(self):
        with mock.patch.dict(os.environ, {"NUXIVA_DUPLEX": "legacy"}):
            service = FakeService(FakePrints())
            self.run_service(service, 10)
            self.assertTrue(service.nuxiva_speaking)
        service = FakeService(FakePrints())
        service.voiceprints.ready = False
        self.run_service(service, 10)
        self.assertTrue(service.nuxiva_speaking)

    def test_a_failing_embedding_counts_as_uncertain(self):
        prints = FakePrints()
        prints.embed = mock.Mock(side_effect=RuntimeError("boom"))
        service = FakeService(prints)
        self.run_service(service, 10)
        self.assertTrue(service.nuxiva_speaking)

    def test_alternating_enrolled_people_never_cut(self):
        class Alternating(FakePrints):
            calls = 0

            def verdict(self, probe):
                Alternating.calls += 1
                return {"slug": "anna" if Alternating.calls % 2 else "luca", "score": 0.85}

            def scores(self, probe):
                return {"anna": 0.85, "luca": 0.85}

        service = FakeService(Alternating())
        self.run_service(service, 40)
        self.assertTrue(service.nuxiva_speaking)

    def test_a_radio_burst_quarantines_the_owner_voice(self):
        service = FakeService(FakePrints())
        service.programme = True
        self.run_service(service, 1)
        service.programme = False
        self.run_service(service, 3)
        self.assertTrue(service.nuxiva_speaking)
        self.run_service(service, 12)
        self.assertFalse(service.nuxiva_speaking)

    @unittest.skipUnless(NATIVE, "modulo nativo non installato")
    def test_native_and_fallback_judge_the_same_windows(self):
        cases = [
            (True, True, 0.85, 0.3, 0.6, False, False, True), (True, True, 0.7, 0.3, 0.6, False, False, True),
            (True, True, 0.85, 0.8, 0.6, False, False, True), (True, False, 0.9, 0.3, 0.6, False, False, True),
            (True, True, 0.9, 0.3, 0.6, True, False, True), (True, True, 0.9, 0.3, 0.6, False, True, True),
            (True, True, 0.9, 0.3, 0.6, False, False, False), (False, True, 0.9, 0.3, 0.6, False, False, True),
            (True, True, float("nan"), 0.3, 0.6, False, False, True),
        ]
        for case in cases:
            self.assertEqual(nuxiva_native.RustBarge.judge_window(*case), barge.PyBarge.judge_window(*case), case)


if __name__ == "__main__":
    unittest.main()
