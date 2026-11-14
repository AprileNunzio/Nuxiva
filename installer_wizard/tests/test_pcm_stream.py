import random
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agenti.voices import pcm_stream

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustPacer")


def wav(rate, channels, samples):
    data = struct.pack(f"<{len(samples)}h", *samples)
    fmt = struct.pack("<HHIIHH", 1, channels, rate, rate * channels * 2, channels * 2, 16)
    return b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(data)) + data


def tone(rate, ms):
    return wav(rate, 1, [i % 200 for i in range(rate * ms // 1000)])


class Contract:
    def make(self, frame_ms=40, lead_ms=240):
        raise NotImplementedError

    def test_frames_have_fixed_duration_and_a_typed_header(self):
        pacer = self.make()
        rate, frames, ms = pacer.push_wav(1, 7, tone(24000, 400))
        self.assertEqual((rate, frames, ms), (24000, 10, 400))
        first = bytes(pacer.poll(0, 1)[0])
        self.assertEqual(first[0], 1)
        self.assertEqual(struct.unpack(">II", first[1:9]), (1, 7))
        self.assertEqual(len(first) - 9, 24000 * 40 // 1000 * 2)

    def test_lead_limits_in_flight_audio_and_cancel_is_immediate(self):
        pacer = self.make()
        pacer.push_wav(1, 1, tone(24000, 2000))
        sent = len(pacer.poll(0, 1))
        self.assertTrue(6 <= sent <= 7)
        self.assertLessEqual(pacer.in_flight_ms(0), 280)
        self.assertEqual(pacer.poll(0, 1), [])
        dropped = pacer.cancel()
        self.assertEqual(dropped[0], 50 - sent)
        self.assertEqual(pacer.queued(), 0)
        self.assertEqual(pacer.poll(10000, 1), [])

    def test_stale_epochs_are_dropped(self):
        pacer = self.make()
        pacer.push_wav(1, 1, tone(24000, 200))
        pacer.push_wav(2, 1, tone(24000, 80))
        out = pacer.poll(0, 2)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(struct.unpack(">I", bytes(f)[1:5])[0] == 2 for f in out))

    def test_hostile_input_is_rejected(self):
        pacer = self.make()
        good = wav(24000, 1, [1, 2, 3, 4])
        bad_tag = bytearray(good)
        bad_tag[20] = 3
        bad_rate = bytearray(good)
        bad_rate[24:28] = struct.pack("<I", 1000)
        for data in (b"", b"RIFF....WAVE", good[:30], bytes(bad_tag), bytes(bad_rate), wav(24000, 1, []), b"\x00" * (17 * 1024 * 1024)):
            with self.assertRaises(ValueError):
                pacer.push_wav(1, 1, data)

    def test_settings_and_capacity_are_bounded(self):
        for args in ((5, 240), (200, 240), (40, 20), (40, 5000)):
            with self.assertRaises(ValueError):
                self.make(*args)
        pacer = self.make()
        big = tone(24000, 60000)
        with self.assertRaises(ValueError):
            for _ in range(4):
                pacer.push_wav(1, 1, big)


class PyContract(Contract, unittest.TestCase):
    def make(self, frame_ms=40, lead_ms=240):
        return pcm_stream.PyPacer(frame_ms, lead_ms)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeContract(Contract, unittest.TestCase):
    def make(self, frame_ms=40, lead_ms=240):
        return nuxiva_native.RustPacer(frame_ms, lead_ms)


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class ParityTest(unittest.TestCase):
    def test_random_sessions_agree(self):
        rng = random.Random(11)
        for _ in range(30):
            frame_ms = rng.choice([10, 20, 40, 100])
            py, rs = pcm_stream.PyPacer(frame_ms, 300), nuxiva_native.RustPacer(frame_ms, 300)
            now = 0
            for step in range(40):
                action = rng.choice(["push", "push", "poll", "poll", "cancel"])
                if action == "push":
                    rate = rng.choice([8000, 16000, 22050, 24000, 48000])
                    channels = rng.choice([1, 2])
                    n = rng.randrange(1, rate // 2) * channels
                    data = wav(rate, channels, [rng.randrange(-32768, 32768) for _ in range(n)])
                    epoch, seq = rng.choice([1, 2]), step
                    self.assertEqual(py.push_wav(epoch, seq, data), rs.push_wav(epoch, seq, data))
                elif action == "poll":
                    now += rng.randrange(0, 120)
                    epoch = rng.choice([1, 2])
                    self.assertEqual(py.poll(now, epoch), [bytes(f) for f in rs.poll(now, epoch)])
                else:
                    self.assertEqual(py.cancel(), rs.cancel())
                self.assertEqual(py.queued(), rs.queued())
                self.assertEqual(py.in_flight_ms(now), rs.in_flight_ms(now))


if __name__ == "__main__":
    unittest.main()
