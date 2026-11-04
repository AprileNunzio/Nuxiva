import sys
import threading
import time
import unittest
from pathlib import Path

VISION = Path(__file__).resolve().parents[1] / "features" / "vision"
if str(VISION) not in sys.path:
    sys.path.append(str(VISION))

from shared_frames import SharedEncoder


class SharedEncoderTest(unittest.TestCase):
    def test_same_frame_is_encoded_once_for_concurrent_viewers(self):
        encoder, calls = SharedEncoder(), []

        def produce():
            calls.append(1)
            time.sleep(0.02)
            return 7, b"jpeg"

        threads = [threading.Thread(target=encoder.get, args=(("live",), 7, produce)) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(encoder.get(("live",), 7, produce), (7, b"jpeg"))
        self.assertEqual(len(calls), 1)

    def test_new_frame_or_variant_triggers_a_new_encode(self):
        encoder = SharedEncoder()
        encoder.get(("live",), 1, lambda: (1, b"a"))
        self.assertEqual(encoder.get(("live",), 2, lambda: (2, b"b")), (2, b"b"))
        self.assertEqual(encoder.get(("hands",), 2, lambda: (2, b"c")), (2, b"c"))
        self.assertEqual(encoder.encodes, 3)

    def test_empty_frames_are_not_cached(self):
        encoder = SharedEncoder()
        encoder.get(("live",), 0, lambda: (0, b""))
        encoder.get(("live",), 0, lambda: (0, b""))
        self.assertEqual(encoder.encodes, 2)

    def test_variants_are_bounded(self):
        encoder = SharedEncoder(limit=2)
        encoder.get((1,), 1, lambda: (1, b"x"))
        encoder.get((2,), 1, lambda: (1, b"x"))
        with self.assertRaises(ValueError):
            encoder.get((3,), 1, lambda: (1, b"x"))


if __name__ == "__main__":
    unittest.main()
