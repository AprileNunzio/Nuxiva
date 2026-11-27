import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

EAR = Path(__file__).resolve().parents[1] / "agenti" / "percezione" / "ear"
if str(EAR) not in sys.path:
    sys.path.append(str(EAR))

import acoustic

RATE = 16000


def _load_stt():
    spec = importlib.util.spec_from_file_location("nuxiva_ear_stt_acoustic", EAR / "stt.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stt = _load_stt()


def word(text, start, end, prob=0.9):
    return SimpleNamespace(word=text, start=start, end=end, probability=prob)


def segment(words, logprob=-0.2):
    return SimpleNamespace(text="".join(w.word for w in words).strip(), words=words, avg_logprob=logprob,
                           no_speech_prob=0.05, compression_ratio=1.2, start=words[0].start, end=words[-1].end)


SPOKEN = [word(" controlla", 0.0, 0.5), word(" i", 0.5, 0.6), word(" dispositivi", 0.6, 1.2), word(" della", 1.2, 1.4),
          word(" casa", 1.4, 1.8)]
INVENTED = [word(" Piano", 2.6, 2.9, 0.3), word(" Piano", 3.0, 3.3, 0.3)]


class AcousticTest(unittest.TestCase):

    def test_spans_are_read_in_seconds_and_hostile_entries_skipped(self):
        found = acoustic.spans([{"start": 3200, "end": 32000}, {"start": 5, "end": 1}, "x", {"start": None, "end": 9}])
        self.assertEqual(found, [(0.2, 2.0)])
        self.assertEqual(acoustic.spans(None), [])

    def test_silence_around_the_voice_is_cut_before_transcription(self):
        audio = np.zeros(RATE * 4, dtype=np.float32)
        clip, offset = acoustic.trim(audio, [(1.0, 2.0)])
        self.assertAlmostEqual(offset, 0.8, places=3)
        self.assertEqual(len(clip), int((2.0 + acoustic.PAD_AFTER_S) * RATE) - int(0.8 * RATE))
        self.assertIs(acoustic.trim(audio, [])[0], audio)

    def test_words_without_voice_under_them_are_dropped_whatever_they_say(self):
        kept, dropped = acoustic.ground([segment(SPOKEN + INVENTED)], [(0.0, 1.85)], 0.0)
        self.assertEqual(kept[0].text, "controlla i dispositivi della casa")
        self.assertEqual(dropped, ["Piano", "Piano"])
        same, none = acoustic.ground([segment(SPOKEN)], [(0.0, 1.85)], 0.0)
        self.assertEqual((same[0].text, none), ("controlla i dispositivi della casa", []))

    def test_offset_of_the_clip_is_respected(self):
        kept, dropped = acoustic.ground([segment(SPOKEN)], [(1.0, 2.85)], 1.0)
        self.assertEqual(dropped, [])
        kept, dropped = acoustic.ground([segment(INVENTED)], [(1.0, 2.85)], 1.0)
        self.assertEqual((kept, dropped), ([], ["Piano", "Piano"]))

    def test_transcription_cuts_silence_and_drops_unvoiced_words(self):
        model = mock.Mock()
        model.transcribe.return_value = ([segment(SPOKEN + INVENTED)], None)
        audio = np.zeros(RATE * 4, dtype=np.float32)
        fixer = mock.Mock()
        fixer.prompt_tail.return_value = ""
        fixer.hear.side_effect = lambda segs, prompt, phrases: SimpleNamespace(
            text=" ".join(s.text for s in segs), confidence=0.9, fixes=(), dropped=())
        with mock.patch.dict(stt.ACTIVE, {"model": model}), mock.patch.object(stt, "FIXER", fixer), \
                mock.patch.object(stt, "get_speech_timestamps", lambda a, o: [{"start": 0, "end": int(1.85 * RATE)}]), \
                mock.patch.object(stt, "VAD", object()), mock.patch.object(stt, "_adapt", lambda *a: None), \
                mock.patch.dict("os.environ", {"NUXIVA_EAR_MODE": "offline"}):
            text, _ = stt.transcribe(audio, fast=False, detect=False)
        self.assertEqual(text, "controlla i dispositivi della casa")
        sent = model.transcribe.call_args.args[0]
        self.assertEqual(len(sent), int((1.85 + acoustic.PAD_AFTER_S) * RATE))


if __name__ == "__main__":
    unittest.main()
