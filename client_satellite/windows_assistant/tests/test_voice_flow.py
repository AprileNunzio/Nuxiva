import json
import threading
import time
import unittest
from pathlib import Path

import numpy as np

from ui.flow import ATTACK, FLOOR, Flow, normalize
from voice.levels import rms_at
from voice.stream import FIRST_LIMIT, NEXT_LIMIT, speak_stream, split_reply


class FlowTest(unittest.TestCase):
    def test_normalize_is_bounded_and_monotonic(self):
        values = [normalize(x / 100) for x in range(0, 30)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values[-1], 1.0)
        self.assertEqual(values, sorted(values))
        self.assertEqual(normalize(-5), 0.0)

    def test_attack_is_faster_than_release(self):
        flow = Flow()
        up = flow.feed(0.05)
        self.assertGreater(up, normalize(0.05) * ATTACK * 0.99)
        peak = flow.amplitude
        flow.feed(0.0)
        self.assertGreater(flow.amplitude, peak * 0.8)

    def test_ribbons_stay_inside_and_taper_at_the_ends(self):
        flow = Flow()
        for _ in range(40):
            flow.feed(1.0)
        for phase in (0.0, 1.3, 7.7):
            for ribbon in flow.ribbons(phase):
                self.assertTrue(all(abs(y) <= 1.0 for y in ribbon))
                self.assertAlmostEqual(ribbon[0], 0.0, places=6)
                self.assertAlmostEqual(ribbon[-1], 0.0, places=6)

    def test_silence_keeps_a_gentle_floor(self):
        flow = Flow()
        peak = max(abs(y) for ribbon in flow.ribbons(0.9) for y in ribbon)
        self.assertGreater(peak, 0.0)
        self.assertLessEqual(peak, FLOOR + 1e-9)


class LevelTest(unittest.TestCase):
    def test_rms_follows_playback_position(self):
        rate = 1000
        audio = np.concatenate([np.zeros(500), np.full(500, 0.5)]).astype(np.float32)
        self.assertAlmostEqual(rms_at(audio, rate, 0.1), 0.0)
        self.assertAlmostEqual(rms_at(audio, rate, 0.6), 0.5, places=5)
        self.assertEqual(rms_at(audio, rate, 5.0), 0.0)


class SplitTest(unittest.TestCase):
    def test_first_chunk_is_a_single_sentence(self):
        chunks = split_reply("Ciao! Sono qui. Ho creato il file richiesto. Vuoi altro?")
        self.assertEqual(chunks[0], "Ciao!")
        self.assertEqual(" ".join(chunks), "Ciao! Sono qui. Ho creato il file richiesto. Vuoi altro?")

    def test_limits_hold_and_no_words_are_lost(self):
        text = " ".join(f"parola{i}" for i in range(400))
        chunks = split_reply(text)
        self.assertLessEqual(len(chunks[0]), FIRST_LIMIT)
        self.assertTrue(all(len(c) <= NEXT_LIMIT for c in chunks))
        self.assertEqual(" ".join(chunks).split(), text.split())

    def test_blank_text_gives_nothing(self):
        self.assertEqual(split_reply("  \n "), [])


class StreamTest(unittest.TestCase):
    def run_stream(self, chunks, fetch, play, cancelled=None):
        events = []
        cancelled = cancelled or threading.Event()
        started = speak_stream(chunks, fetch, play, cancelled, lambda: events.append("first"),
                               lambda exc: events.append(("error", str(exc))), (ValueError,))
        return started, events

    def test_next_chunk_is_fetched_while_the_previous_one_plays(self):
        timeline = []

        def fetch(chunk):
            time.sleep(0.15)
            timeline.append(("fetched", chunk, time.monotonic()))
            return chunk.encode()

        def play(data):
            timeline.append(("play", data.decode(), time.monotonic()))
            time.sleep(0.3)

        began = time.monotonic()
        started, events = self.run_stream(["a", "b", "c"], fetch, play)
        total = time.monotonic() - began
        self.assertTrue(started)
        self.assertEqual(events, ["first"])
        self.assertEqual([e[1] for e in timeline if e[0] == "play"], ["a", "b", "c"])
        self.assertLess(total, 0.15 + 3 * 0.3 + 0.2)
        first_play = next(e[2] for e in timeline if e[0] == "play")
        self.assertLess(first_play - began, 0.3)

    def test_error_before_audio_reports_and_never_starts(self):
        def fetch(chunk):
            raise ValueError("offline")

        started, events = self.run_stream(["a", "b"], fetch, lambda data: None)
        self.assertFalse(started)
        self.assertEqual(events, [("error", "offline")])

    def test_error_midway_stops_after_what_was_played(self):
        played = []

        def fetch(chunk):
            if chunk == "b":
                raise ValueError("lost")
            return chunk.encode()

        started, events = self.run_stream(["a", "b", "c"], fetch, lambda data: played.append(data))
        self.assertTrue(started)
        self.assertEqual(played, [b"a"])
        self.assertEqual(events, ["first", ("error", "lost")])

    def test_cancel_stops_playback_and_the_prefetcher(self):
        cancelled = threading.Event()
        played = []

        def play(data):
            played.append(data)
            cancelled.set()

        started, _ = self.run_stream(["a", "b", "c", "d", "e"], lambda c: c.encode(), play, cancelled)
        self.assertTrue(started)
        self.assertEqual(played, [b"a"])


class DictionaryTest(unittest.TestCase):
    def test_every_language_has_the_same_keys(self):
        folder = Path(__file__).resolve().parent.parent / "i18n"
        tables = {lang: json.loads((folder / f"{lang}.json").read_text(encoding="utf-8"))
                  for lang in ("it", "en", "fr", "es")}
        reference = set(tables["it"])
        for lang, table in tables.items():
            self.assertEqual(set(table), reference, lang)
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in table.values()), lang)


if __name__ == "__main__":
    unittest.main()
