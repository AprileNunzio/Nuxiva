import threading
import unittest

import numpy as np

from autonomy import profile
from autonomy.local_ear import LocalEar
from autonomy.sapi_stt import write_wav
from autonomy.segmenter import FRAME, Segmenter
from autonomy.tts import MAX_CHARS, clamp, culture_for
from autonomy.wake import WakeGate


class ProfileTest(unittest.TestCase):
    def test_tiers_scale_with_hardware(self):
        cases = {
            profile.Hardware(32, 128.0, "RTX 5090", 32.0): "workstation",
            profile.Hardware(16, 32.0, "RTX 4070", 12.0): "performance",
            profile.Hardware(8, 16.0, "", 0.0): "standard",
            profile.Hardware(4, 8.0, "", 0.0): "light",
            profile.Hardware(2, 4.0, "", 0.0): "minimal",
        }
        for hardware, name in cases.items():
            self.assertEqual(profile.recommend(hardware).name, name)

    def test_pick_model_prefers_choice_then_tier_then_family(self):
        tier = profile.TIERS[2]
        self.assertEqual(profile.pick_model(tier, ["qwen3:4b", "llama3:8b"], "llama3:8b"), "llama3:8b")
        self.assertEqual(profile.pick_model(tier, ["qwen3:4b", "x:1"]), "qwen3:4b")
        self.assertEqual(profile.pick_model(tier, ["qwen3:30b-a3b"]), "qwen3:30b-a3b")
        self.assertEqual(profile.pick_model(tier, ["mistral:7b"]), "")

    def test_resolve_follows_the_chosen_mode(self):
        M = profile.Mode
        self.assertEqual(profile.resolve(M.SERVER, False, True), "none")
        self.assertEqual(profile.resolve(M.LOCAL, True, True), "local")
        self.assertEqual(profile.resolve(M.LOCAL, True, False), "none")
        self.assertEqual(profile.resolve(M.AUTO, True, True), "server")
        self.assertEqual(profile.resolve(M.AUTO, False, True), "local")
        self.assertEqual(profile.resolve(M.AUTO, False, False), "none")

    def test_unknown_mode_falls_back_to_auto(self):
        self.assertIs(profile.parse_mode("boh"), profile.Mode.AUTO)
        self.assertIs(profile.parse_mode("LOCAL"), profile.Mode.LOCAL)


class WakeTest(unittest.TestCase):
    def setUp(self):
        self.gate = WakeGate(lambda: ["Aria", "Nuxiva"])

    def test_name_with_command(self):
        remainder, kind = self.gate.process("Ehi Aria, che ora è?", now=0)
        self.assertEqual(kind, "wake")
        self.assertEqual(remainder, "che ora e")
        self.assertEqual(self.gate.command_text("Ehi Aria, che ora è?", remainder), "che ora è")

    def test_fuzzy_name_and_second_name(self):
        self.assertEqual(self.gate.process("nuxiva apri le note", now=0)[1], "wake")
        self.assertEqual(self.gate.process("aria spegni la luce", now=0)[1], "wake")

    def test_other_speech_is_ignored_until_followup(self):
        self.assertIsNone(self.gate.process("domani vado al mare", now=0))
        self.gate.open_followup(8, now=0)
        self.assertEqual(self.gate.process("e dopodomani", now=5), ("e dopodomani", "followup"))
        self.assertIsNone(self.gate.process("e dopodomani", now=20))

    def test_name_only(self):
        self.assertEqual(self.gate.process("Aria", now=0), ("", "wake"))


class SegmenterTest(unittest.TestCase):
    def pcm(self, amplitude, frames):
        rng = np.random.default_rng(3)
        return (rng.normal(0, amplitude, frames * FRAME) * 32767).astype(np.int16).tobytes()

    def test_one_utterance_is_cut_after_silence(self):
        seg, out = Segmenter(), []
        for chunk in (self.pcm(0.002, 20), self.pcm(0.1, 30), self.pcm(0.002, 40)):
            out += seg.feed(chunk)
        self.assertEqual(len(out), 1)
        self.assertGreater(len(out[0]) // 2 // FRAME, 30)

    def test_noise_alone_gives_nothing(self):
        seg = Segmenter()
        self.assertEqual(seg.feed(self.pcm(0.003, 200)), [])

    def test_odd_chunk_sizes_are_buffered(self):
        seg, out = Segmenter(), []
        data = self.pcm(0.002, 20) + self.pcm(0.1, 30) + self.pcm(0.002, 40)
        for i in range(0, len(data), 1000):
            out += seg.feed(data[i:i + 1000])
        self.assertEqual(len(out), 1)


class FakeEngine:
    def __init__(self, text):
        self.text = text

    def ready(self):
        return True

    def transcribe(self, pcm, lang=None):
        return self.text, "it"


class LocalEarTest(unittest.TestCase):
    def run_ear(self, text, forced=False):
        events, done = [], threading.Event()

        def on_event(event):
            events.append(event)
            if event["type"] in ("transcript", "wake_only") or (event["type"] == "state" and event["state"] == "idle"):
                done.set()

        ear = LocalEar(FakeEngine(text), lambda: ["Aria"], on_event)
        ear.start()
        if forced:
            ear.send(type="listen")
        ear.jobs.put(b"\0\0" * 1000)
        self.assertTrue(done.wait(3))
        ear.stop()
        return [e["type"] if e["type"] != "state" else e["state"] for e in events], events

    def test_directed_speech_becomes_a_transcript(self):
        kinds, events = self.run_ear("Aria apri il browser")
        self.assertEqual(kinds, ["transcribing", "wake", "transcript"])
        self.assertEqual(events[-1]["text"], "apri il browser")

    def test_undirected_speech_is_dropped(self):
        kinds, _ = self.run_ear("parlavo con un amico")
        self.assertEqual(kinds, ["transcribing", "idle"])

    def test_push_to_talk_accepts_anything(self):
        kinds, events = self.run_ear("che tempo fa", forced=True)
        self.assertEqual(kinds[-1], "transcript")
        self.assertEqual(events[-1]["text"], "che tempo fa")


class SpeechTest(unittest.TestCase):
    def test_culture_and_clamp(self):
        self.assertEqual(culture_for("it-IT"), "it-IT")
        self.assertEqual(culture_for("fr"), "fr-FR")
        self.assertEqual(culture_for("xx"), "en-US")
        self.assertEqual(culture_for(None), "it-IT")
        self.assertEqual(len(clamp("a " * 2000)), MAX_CHARS)
        self.assertEqual(clamp("  a \n b "), "a b")


class WavTest(unittest.TestCase):
    def test_pcm_is_wrapped_as_16k_mono(self):
        import tempfile
        import wave
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "a.wav"
            write_wav(target, b"\x01\x00" * 160)
            with wave.open(str(target)) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()), (1, 2, 16000, 160))


if __name__ == "__main__":
    unittest.main()
