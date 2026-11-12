import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.chat.intents import detect_intent
from agenti.ear import endpoint
from agenti.ear.array_capture import parse_sources, source_command
from agenti.ear.mic_array import MicArray, PyMicArray, pick_best

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustMicArray") and hasattr(NATIVE, "RustEndpointer")
RATE = 16000
FRAME = 480


def voice(n, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / RATE
    envelope = np.maximum(np.sin(2 * np.pi * 3 * t), 0)
    tone = np.sin(2 * np.pi * 180 * t) + 0.5 * np.sin(2 * np.pi * 360 * t)
    return (0.2 * envelope * (0.6 * tone + 0.4 * rng.standard_normal(n))).astype(np.float32)


def noise(n, seed, gain):
    return (gain * np.random.default_rng(seed).standard_normal(n)).astype(np.float32)


def run(engine, channels):
    bests = []
    for start in range(0, len(channels[0]) - FRAME + 1, FRAME):
        frames = [c[start:start + FRAME].astype("<f4").tobytes() for c in channels]
        _, best, _, _ = engine.mix(frames)
        bests.append(best)
    return bests


def drive(engine, script):
    t, ends = 0.0, []
    for action, seconds in script:
        if action == "begin":
            engine.begin(t)
            continue
        if action == "wake":
            engine.wake()
            continue
        stop = t + seconds
        while t < stop:
            reason = engine.frame(t, action == "voice")
            if reason:
                ends.append((round(t, 2), reason))
            t += 0.03
    return ends


SCRIPTS = (
    [("begin", 0), ("voice", 0.6), ("wake", 0), ("quiet", 1.0), ("voice", 1.4), ("quiet", 2.0)],
    [("begin", 0), ("voice", 0.6), ("wake", 0), ("quiet", 3.0)],
    [("begin", 0), ("voice", 1.0), ("quiet", 2.0)],
    [("begin", 0), ("voice", 16.0)],
)


class MicArrayParityTest(unittest.TestCase):

    def scenes(self):
        n = RATE * 4
        speech = voice(n, 1)
        return (
            [speech * 0.3 + noise(n, 2, 0.05), speech + noise(n, 3, 0.01)],
            [np.zeros(n, dtype=np.float32), speech + noise(n, 4, 0.01)],
            [speech + noise(n, 5, 0.005), speech * 0.5 + noise(n, 6, 0.08), noise(n, 7, 0.02)],
        )

    def test_python_picks_the_clearest_microphone(self):
        expected = (1, 1, 0)
        for scene, best in zip(self.scenes(), expected):
            self.assertEqual(run(PyMicArray(len(scene)), scene)[-1], best)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_rust_and_python_agree_on_the_best_microphone(self):
        for scene in self.scenes():
            rust = run(NATIVE.RustMicArray(len(scene)), scene)
            python = run(PyMicArray(len(scene)), scene)
            self.assertEqual(rust[-1], python[-1])

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_rust_fuses_two_microphones_hearing_the_same_voice(self):
        n = RATE * 5
        speech = voice(n, 8)
        late = np.concatenate([np.zeros(200, dtype=np.float32), speech[:-200]])
        array = NATIVE.RustMicArray(2)
        fused = 0
        for start in range(0, n - FRAME + 1, FRAME):
            frames = [(speech[start:start + FRAME] + noise(FRAME, start, 0.04)).astype("<f4").tobytes(),
                      (late[start:start + FRAME] + noise(FRAME, start + 1, 0.04)).astype("<f4").tobytes()]
            _, _, fused, _ = array.mix(frames)
        self.assertEqual(fused, 2)

    def test_malformed_frames_are_rejected(self):
        engines = [PyMicArray(2)] + ([NATIVE.RustMicArray(2)] if READY else [])
        for engine in engines:
            with self.assertRaises(ValueError):
                engine.mix([b"\x00" * 1920])
            with self.assertRaises(ValueError):
                engine.mix([b"\x00" * 1920, b"\x00" * 1916])
        with self.assertRaises(ValueError):
            PyMicArray(9)

    def test_switching_needs_a_lasting_lead(self):
        streak = [0, 0]
        self.assertEqual(pick_best([10.0, 11.0], 0, streak), 0)
        picks = [pick_best([10.0, 14.0], 0, streak) for _ in range(10)]
        self.assertEqual(picks[-1], 1)
        self.assertEqual(picks[0], 0)

    def test_pcm_wrapper_returns_int16_of_the_same_length(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            array = MicArray(2)
        pcm = (np.full(FRAME, 1000, dtype="<i2")).tobytes()
        out = array.mix_pcm([pcm, bytes(len(pcm))])
        self.assertEqual(len(out), len(pcm))
        self.assertFalse(array.native)


class EndpointParityTest(unittest.TestCase):

    def test_pause_after_the_name_keeps_the_sentence_together(self):
        engine = endpoint.PyEndpointer(**endpoint.config())
        ends = drive(engine, SCRIPTS[0])
        self.assertEqual(len(ends), 1)
        self.assertEqual(ends[0][1], "silence")
        self.assertGreater(ends[0][0], 3.0)

    def test_lone_name_waits_longer_than_normal_silence(self):
        engine = endpoint.PyEndpointer(**endpoint.config())
        self.assertEqual(drive(engine, SCRIPTS[1])[0][1], "wake_hold")

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_rust_and_python_end_utterances_at_the_same_moment(self):
        for script in SCRIPTS:
            rust = drive(NATIVE.RustEndpointer(**endpoint.config()), script)
            python = drive(endpoint.PyEndpointer(**endpoint.config()), script)
            self.assertEqual(rust, python)

    def test_config_is_bounded(self):
        with mock.patch.dict("os.environ", {"NUXIVA_EAR_END_SILENCE": "9", "NUXIVA_EAR_WAKE_HOLD": "0.1"}):
            cfg = endpoint.config()
        self.assertEqual(cfg["end_silence"], 1.5)
        self.assertGreaterEqual(cfg["wake_hold"], cfg["end_silence"])


class SourcesTest(unittest.TestCase):

    def test_monitors_and_unsafe_names_are_skipped(self):
        listing = ("0\talsa_output.pci.monitor\tmodule\ts16le\tIDLE\n"
                   "1\talsa_input.usb-Webcam-00.mono-fallback\tmodule\ts16le\tRUNNING\n"
                   "2\talsa_input.pci-0000_00_1f.3.analog-stereo\tmodule\ts16le\tSUSPENDED\n"
                   "3\tbad;rm -rf /\tmodule\ts16le\tIDLE\n"
                   "garbage\n")
        self.assertEqual(parse_sources(listing), ["alsa_input.usb-Webcam-00.mono-fallback",
                                                  "alsa_input.pci-0000_00_1f.3.analog-stereo"])

    def test_source_command_has_no_shell_and_validates_the_name(self):
        cmd = source_command([], "alsa_input.usb-Webcam", 30)
        self.assertEqual(cmd[:2], ["parec", "--device=alsa_input.usb-Webcam"])
        with self.assertRaises(ValueError):
            source_command([], "x; reboot", 30)


class WeatherIntentTest(unittest.TestCase):

    def test_weather_questions_survive_imperfect_transcripts(self):
        for text in ("Che tempo fa domani", "E tempo fa domani.", "tempo domani?", "Farà freddo domani?",
                     "Serve l'ombrello?", "che tempo ci sarà nel weekend", "Com'è il tempo oggi"):
            self.assertEqual(detect_intent(text), "weather", text)

    def test_other_uses_of_tempo_are_not_weather(self):
        self.assertNotEqual(detect_intent("quanto tempo ci vuole per arrivare a Roma"), "weather")
