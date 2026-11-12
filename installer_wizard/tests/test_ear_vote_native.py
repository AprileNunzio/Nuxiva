import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.ear import vote as vote_mod
from agenti.ear.array_capture import ArrayCapture

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "ear_vote")

CASES = (
    [("Jarvis e tempo fa domani", 1.5), ("Jarvis che tempo fa domani", 1.0), ("Jarvis che tempo fa domani?", 1.0)],
    [("tempo fa domani", 1.5), ("che tempo fa domani", 1.0), ("che tempo fa domani", 1.0)],
    [("accendi la luce", 1.5), ("accendi la luce grazie", 1.0), ("accendi la luce", 1.0)],
    [("accendi la luce", 1.0), ("Accendi la luce.", 1.0)],
    [("spegni", 2.0), ("spengo", 1.0)],
    [("metti la musica in cucina", 1.5), ("metti musica in cucina", 0.9), ("metti la musica in cucina per favore", 0.8)],
    [],
    [("", 1.0), ("ciao", float("nan"))],
)


class VoteTest(unittest.TestCase):

    def test_majority_repairs_what_one_microphone_misheard(self):
        self.assertEqual(vote_mod.py_vote(list(CASES[0]))[0], "Jarvis che tempo fa domani")
        self.assertEqual(vote_mod.py_vote(list(CASES[1]))[0], "che tempo fa domani")
        self.assertEqual(vote_mod.py_vote(list(CASES[2]))[0], "accendi la luce")
        text, agreement, changed = vote_mod.py_vote(list(CASES[3]))
        self.assertAlmostEqual(agreement, 1.0)
        self.assertEqual(changed, 0)

    def test_hostile_input_is_bounded(self):
        self.assertEqual(vote_mod.py_vote([]), ("", 0.0, 0))
        text, _, _ = vote_mod.vote([("parola " * 5000, 1.0)] * 20)
        self.assertLessEqual(len(text.split()), vote_mod.MAX_WORDS)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_rust_and_python_vote_the_same(self):
        for case in CASES:
            rust = NATIVE.ear_vote(list(case))
            python = vote_mod.py_vote(list(case))
            self.assertEqual(rust[0], python[0], case)
            self.assertEqual(rust[2], python[2], case)
            self.assertAlmostEqual(rust[1], python[1], places=4)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_rust_rejects_oversized_requests(self):
        with self.assertRaises(ValueError):
            NATIVE.ear_vote([("a", 1.0)] * 9)


class ConsensusTest(unittest.IsolatedAsyncioTestCase):

    async def test_each_microphone_transcribes_and_the_vote_decides(self):
        from agenti.ear import consensus

        class Provider:
            def recent(self, samples):
                pcm = np.zeros(samples, dtype="<i2").tobytes()
                return [("webcam", 18.0, pcm), ("laptop", 22.0, pcm), ("muto", -100.0, pcm)]

        heard = iter(["Jarvis che tempo fa domani", "Jarvis che tempo fa domani"])
        stub = SimpleNamespace(HOME_LANG="it", transcribe=lambda *a: (next(heard), "it"), hallucination=lambda t: False)
        with mock.patch.object(consensus, "stt", stub), \
             mock.patch.dict("os.environ", {"NUXIVA_EAR_MODE": "offline"}):
            text = await consensus.agree(Provider(), np.zeros(16000, dtype=np.float32), "Jarvis e tempo fa domani", "it")
        self.assertEqual(text, "Jarvis che tempo fa domani")

    async def test_nothing_changes_without_several_microphones_or_when_disabled(self):
        from agenti.ear import consensus
        clean = np.zeros(1600, dtype=np.float32)
        self.assertEqual(await consensus.agree(None, clean, "ciao", "it"), "ciao")
        provider = mock.Mock()
        provider.recent.return_value = [("solo", 20.0, b"\x00\x00")]
        stub = SimpleNamespace(HOME_LANG="it", transcribe=mock.Mock(), hallucination=lambda t: False)
        with mock.patch.object(consensus, "stt", stub):
            self.assertEqual(await consensus.agree(provider, clean, "ciao", "it"), "ciao")
            with mock.patch.dict("os.environ", {"NUXIVA_EAR_VOTE": "0"}):
                self.assertEqual(await consensus.agree(provider, clean, "ciao", "it"), "ciao")

    def test_noisy_or_silent_microphones_are_not_asked(self):
        from agenti.ear import consensus
        picked = consensus.pick([("a", 3.0, b"x"), ("b", 25.0, b"x"), ("c", 12.0, b"x"), ("d", 30.0, b"")], 2)
        self.assertEqual([c[0] for c in picked], ["b", "c"])


class RecentAudioTest(unittest.TestCase):

    def test_capture_keeps_the_raw_audio_of_every_microphone(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            capture = ArrayCapture(["a", "b"], [], 30)
        for feed in capture.feeds:
            feed.buf.extend(np.full(480 * 4, 100, dtype="<i2").tobytes())
        frames = 0
        while capture._take() is not None:
            frames += 1
        self.assertEqual(frames, 4)
        recent = capture.recent(480)
        self.assertEqual([r[0] for r in recent], ["a", "b"])
        self.assertTrue(all(len(r[2]) == 960 for r in recent))
        self.assertEqual(capture.recent(0)[0][2], b"")
        asyncio.run(capture.stop())
