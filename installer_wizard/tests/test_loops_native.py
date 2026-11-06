import sys
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import loops
import native_core
from tests.test_scheduler import LoopsTest

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustLoopBook")


def python_delays(failures: int, durations: list[float], minimum: float, maximum: float, stable: float) -> list[float]:
    delay, out = minimum, []
    for index in range(failures):
        if durations[index] > stable:
            delay = minimum
        out.append(delay)
        delay = min(delay * 2, maximum)
    return out


@unittest.skipUnless(READY, "modulo nativo supervisor-core non installato")
class RustLoopsScenarios(LoopsTest):

    def test_engine_is_rust(self):
        self.assertIsNotNone(loops.Supervisor().book)


@unittest.skipUnless(READY, "modulo nativo supervisor-core non installato")
class PolicyParityTest(unittest.TestCase):

    def test_backoff_sequence_matches_python(self):
        for durations in ([1.0] * 8, [1.0, 1.0, 500.0, 1.0, 1.0, 1.0, 200.0, 1.0], [130.0] * 8):
            with self.subTest(durations=durations):
                book, now, got = NATIVE.RustLoopBook(), 0.0, []
                book.add("x", 0.0, now)
                for duration in durations:
                    book.start("x", now)
                    now += duration
                    action, delay, _, _ = book.exit("x", "failed", "e", now, True, 1.0, 60.0, 120.0, 10)
                    self.assertEqual(action, "restart")
                    got.append(delay)
                self.assertEqual(got, python_delays(len(durations), durations, 1.0, 60.0, 120.0))

    def test_report_rule_matches_python(self):
        book = NATIVE.RustLoopBook()
        book.add("x", 0.0, 0.0)
        for attempt in range(1, 31):
            book.start("x", 0.0)
            _, _, report, restarts = book.exit("x", "cancelled", "bloccato", 0.0, True, 1.0, 60.0, 120.0, 10)
            self.assertEqual(restarts, attempt)
            self.assertEqual(report, attempt == 1 or attempt % 10 == 0)

    def test_invalid_outcome_is_refused(self):
        book = NATIVE.RustLoopBook()
        book.add("x", 0.0, 0.0)
        with self.assertRaises(ValueError):
            book.exit("x", "exploded", "", 0.0, True, 1.0, 60.0, 120.0, 10)


class PythonLoopsScenarios(LoopsTest):

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(native_core, "symbol", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_engine_is_python(self):
        self.assertIsNone(loops.Supervisor().book)


del LoopsTest

if __name__ == "__main__":
    unittest.main()
