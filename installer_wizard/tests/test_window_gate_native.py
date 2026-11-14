import random
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EAR = str(ROOT / "agenti" / "percezione" / "ear")
if EAR not in sys.path:
    sys.path.insert(0, EAR)

import window_gate

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustGate")


def frame(n=480, value=0.1):
    return struct.pack(f"<{n}f", *([value] * n))


def judge_args(**over):
    base = {"voiced": True, "has_match": True, "score": 0.85, "runner_up": 0.3, "limit": 0.6, "music": False, "programme": False, "echo_cancelled": True}
    base.update(over)
    return tuple(base.values())


class Contract:
    def make(self):
        raise NotImplementedError

    def test_nine_frames_close_one_window_until_released(self):
        gate = self.make()
        for _ in range(8):
            self.assertIsNone(gate.push(frame(), True))
        raw, voiced = gate.push(frame(), True)
        self.assertEqual(len(raw), 4000 * 4)
        self.assertTrue(voiced)
        self.assertTrue(gate.busy())
        for _ in range(30):
            self.assertIsNone(gate.push(frame(), True))
        gate.release()
        self.assertIsNotNone(gate.push(frame(), True))

    def test_hostile_frames_are_never_voiced(self):
        gate = self.make()
        poison = struct.pack("<480f", *([float("nan")] * 480))
        out = None
        for _ in range(9):
            out = gate.push(poison, True)
        raw, voiced = out
        self.assertFalse(voiced)
        self.assertTrue(all(v == 0.0 for v in struct.unpack("<4000f", raw)))
        gate.release()
        self.assertIsNone(gate.push(b"", True))
        self.assertIsNone(gate.push(frame(20000), True))

    def test_the_owner_needs_a_settled_slug_and_broadcast_quarantines(self):
        gate = self.make()
        self.assertEqual(gate.judge(*judge_args(), "anna")[0], "uncertain")
        self.assertEqual(gate.judge(*judge_args(), "anna")[0], "known")
        self.assertEqual(gate.judge(*judge_args(music=True), None)[0], "broadcast")
        self.assertTrue(gate.quarantined())
        for _ in range(8):
            self.assertNotEqual(gate.judge(*judge_args(), "anna")[0], "known")
        self.assertEqual(gate.judge(*judge_args(), "anna")[0], "uncertain")
        self.assertEqual(gate.judge(*judge_args(), "anna")[0], "known")

    def test_changing_person_or_invalid_slug_is_never_known(self):
        gate = self.make()
        for i in range(30):
            self.assertNotEqual(gate.judge(*judge_args(), "anna" if i % 2 else "luca")[0], "known")
        for slug in (None, "", "a b", "é", "x" * 65):
            for _ in range(4):
                self.assertNotEqual(gate.judge(*judge_args(), slug)[0], "known")


class PyContract(Contract, unittest.TestCase):
    def make(self):
        return window_gate.PyGate()


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeContract(Contract, unittest.TestCase):
    def make(self):
        return nuxiva_native.RustGate()


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class ParityTest(unittest.TestCase):
    def test_random_streams_agree(self):
        rng = random.Random(7)
        for _ in range(40):
            py, rs = window_gate.PyGate(), nuxiva_native.RustGate()
            for _ in range(300):
                n = rng.choice([160, 480, 1000, 2000, 4000])
                value = rng.choice([0.0, 0.2, -0.3, float("nan"), float("inf")])
                data, voiced = frame(n, value), rng.random() < 0.7
                a, b = py.push(data, voiced), rs.push(data, voiced)
                self.assertEqual(a is None, b is None)
                if a is not None:
                    self.assertEqual(a[1], b[1])
                    self.assertEqual(a[0], bytes(b[0]))
                    py.release()
                    rs.release()
                    args = judge_args(
                        voiced=rng.random() < 0.8, has_match=rng.random() < 0.8, score=rng.choice([0.2, 0.7, 0.85, 0.95, float("nan")]),
                        runner_up=rng.choice([0.1, 0.3, 0.8]), limit=0.6, music=rng.random() < 0.1, programme=rng.random() < 0.1,
                        echo_cancelled=rng.random() < 0.9,
                    )
                    slug = rng.choice(["anna", "luca", None, "", "a b"])
                    self.assertEqual(tuple(py.judge(*args, slug)), tuple(rs.judge(*args, slug)))
                    self.assertEqual(py.quarantined(), rs.quarantined())
                if rng.random() < 0.01:
                    py.reset()
                    rs.reset()


if __name__ == "__main__":
    unittest.main()
