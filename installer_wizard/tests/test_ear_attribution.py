import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
import attribution

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustAttributor")
DIM = 64


def noisy(rng, base, amount):
    return (base + amount * rng.standard_normal(DIM)).astype(np.float32)


def sequence(seed):
    rng = np.random.default_rng(seed)
    owner, radio = rng.standard_normal(DIM), rng.standard_normal(DIM)
    steps = []
    for index in range(60):
        kind = rng.integers(0, 4)
        base = owner if kind < 2 else radio if kind == 2 else 0.5 * owner + 0.5 * radio
        probe = noisy(rng, base, 0.3)
        score = float(np.clip(0.45 + 0.4 * rng.random() + (0.1 if kind < 2 else -0.1), 0.0, 1.0))
        slug = "nunzio" if score >= 0.58 else None
        windows = [] if rng.random() < 0.5 else [("nunzio" if rng.random() < 0.7 else None, float(0.5 + 0.4 * rng.random())) for _ in range(3)]
        steps.append((probe, slug, score, 0.58, float(0.5 + 3 * rng.random()), bool(rng.random() < 0.3), windows, float(index) * 2.5))
    return steps


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class AttributionParityTest(unittest.TestCase):

    def test_native_and_python_give_the_same_verdicts(self):
        for seed in range(12):
            rust, py = attribution.build(), attribution.PyAttributor()
            for step in sequence(seed):
                a = rust.judge(step[0].tolist(), *step[1:])
                b = py.judge(*step)
                self.assertEqual((a["slug"], a["verified"], a["foreign"], a["reason"]),
                                 (b["slug"], b["verified"], b["foreign"], b["reason"]), (seed, step[2]))
            self.assertEqual(rust.foreign_count(), py.foreign_count())
            self.assertEqual(rust.foreign_recent(150.0, 120.0), py.foreign_recent(150.0, 120.0))

    def test_invalid_input_is_rejected(self):
        engine = NATIVE.RustAttributor()
        with self.assertRaises(ValueError):
            engine.judge([], None, 0.5, 0.6, 3.0, False, [], 0.0)
        out = engine.judge([float("nan")] * 4, "nunzio", 0.9, 0.6, 3.0, False, [], 0.0)
        self.assertFalse(out["verified"])
        self.assertEqual(out["reason"], "dati non validi")


class PythonAttributorTest(unittest.TestCase):

    def test_owner_short_and_programme_cases(self):
        rng = np.random.default_rng(3)
        owner = rng.standard_normal(DIM)
        gate = attribution.PyAttributor()
        probe = noisy(rng, owner, 0.1)
        self.assertTrue(gate.judge(probe, "nunzio", 0.9, 0.6, 3.0, False, [], 0.0)["verified"])
        self.assertEqual(gate.judge(probe, "nunzio", 0.9, 0.6, 0.5, False, [], 1.0)["reason"], "troppo breve")
        self.assertEqual(gate.judge(probe, "nunzio", 0.66, 0.6, 3.0, False, [], 2.0)["reason"], "ok")
        busy = attribution.PyAttributor()
        self.assertEqual(busy.judge(probe, "nunzio", 0.66, 0.6, 3.0, True, [], 0.0)["reason"], "prova insufficiente")

    def test_fallback_is_used_without_the_native_module(self):
        from unittest import mock
        with mock.patch.object(native_core, "symbol", return_value=None):
            self.assertIsInstance(attribution.build(), attribution.PyAttributor)


if __name__ == "__main__":
    unittest.main()
