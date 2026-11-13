import asyncio
import random
import time
import unittest
from unittest import mock

import native_core
from agenti.music import commands, karaoke, lyrics
from agenti.music.algorithms import lrc
from agenti.music.algorithms.song_clock import PySongClock, SongClock
from config import write_env
from state import store
from tests.test_music_library import Base

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "lyrics_parse") and hasattr(NATIVE, "RustSongClock")

SAMPLES = [
    "[00:12.50]Seconda\n[00:01.2]Prima\n[ar:Artista]\nsenza tempo\n",
    "[01:02.5]a\n[01:02.05]b\n[01:02.005]c\n[01:02:50]d\n[1:02]e",
    "[00:10.00][00:40.00]Ritornello\n[00:20.00]\n",
    "[00:75.00]no\n[aa:10]no\n[0000:10]no\n[00:1]no\n[00:10.1234]no\n[00:05]si",
    "[offset:+500]\n[00:10.00]a <00:10.20>b\n[00:00.20]c\n[offset:-250]\n[00:30.00]z",
    "[00:05.00]<00:05.00>Nel <00:05.40>blu <00:06.10>dipinto",
    "[00:01.00]a < b <tag> c\n[00:02.00]  ciao\u0007\tmondo   bello \r\n",
    "[00:01.00]" + "x" * 500 + "\n" + "".join(f"[{i // 60:02d}:{i % 60:02d}.00]r{i}\n" for i in range(600)),
    "",
]


class ParserTest(unittest.TestCase):
    def test_python_parser_basics(self):
        got = [(l["t"], l["text"]) for l in lrc._py_parse(SAMPLES[0])]
        self.assertEqual(got, [(1200, "Prima"), (12500, "Seconda")])
        words = lrc._py_parse(SAMPLES[5])[0]["words"]
        self.assertEqual([(w["t"], w["text"]) for w in words], [(5000, "Nel"), (5400, "blu"), (6100, "dipinto")])
        self.assertEqual(len(lrc._py_parse(SAMPLES[7])), lrc.MAX_LINES)

    def test_seconds_wrapper(self):
        rows = lrc.parse("[00:01.50]<00:01.50>ciao <00:02.00>mondo")
        self.assertEqual(rows[0]["t"], 1.5)
        self.assertEqual(rows[0]["words"][1], {"t": 2.0, "text": "mondo"})
        self.assertEqual(lyrics._parse("[01:05.25]due")[0]["t"], 65.25)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_native_parity(self):
        import json
        for sample in SAMPLES:
            with self.subTest(sample=sample[:30]):
                self.assertEqual(json.loads(NATIVE.lyrics_parse(sample)), lrc._py_parse(sample))

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_native_parity_random(self):
        rng = random.Random(7)
        parts = ["[00:0{}.{}]", "<00:0{}.{}>", "ciao ", "mondo", " ", "<", "[offset:{}]\n", "\n", "[01:{}0.5]"]
        for _ in range(300):
            text = "".join(rng.choice(parts).format(rng.randrange(10), rng.randrange(100)) for _ in range(rng.randrange(1, 14)))
            self.assertEqual(__import__("json").loads(NATIVE.lyrics_parse(text)), lrc._py_parse(text), text)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_native_rejects_huge_input(self):
        with self.assertRaises(ValueError):
            NATIVE.lyrics_parse("x" * (lrc.MAX_INPUT * 2 + 1))


class ClockTest(unittest.TestCase):
    def test_smoothing_and_outlier(self):
        clock = SongClock(PySongClock())
        self.assertEqual(clock.observe(100.0, 30.0), (70.0, True))
        self.assertEqual(clock.observe(160.0, 89.4)[0], 70.3)
        outlier = clock.observe(210.0, 60.0)
        self.assertFalse(outlier[1])
        self.assertAlmostEqual(outlier[0], 70.3, places=3)
        jump = clock.observe(220.0, 70.4)
        self.assertTrue(jump[1])
        self.assertAlmostEqual(jump[0], 149.8, places=1)

    @unittest.skipUnless(READY, "nuxiva_native non disponibile")
    def test_native_parity(self):
        rng = random.Random(3)
        for _ in range(40):
            a, b = NATIVE.RustSongClock(), PySongClock()
            wall = 1_700_000_000_000
            origin = 5_000
            for _ in range(60):
                wall += rng.randrange(1000, 9000)
                noise = rng.choice([0, 0, rng.randrange(-700, 700), rng.randrange(-40_000, 40_000)])
                pos = wall - origin + noise
                self.assertEqual(a.observe(wall, pos), b.observe(wall, pos))


class KaraokeSkillTest(Base):
    def setUp(self):
        super().setUp()
        write_env({"NUXIVA_MUSIC_KARAOKE": "0"})
        karaoke.loaded.clear()
        karaoke.pending.clear()
        self.addCleanup(lambda: setattr(store, "now_playing", {}))
        self.addCleanup(lambda: write_env({"NUXIVA_MUSIC_KARAOKE": "0"}))

    def test_phrases(self):
        self.assertTrue(commands.karaoke_request(commands.plain("Abilità karaoke")))
        self.assertTrue(commands.karaoke_request(commands.plain("attiva il karaoke")))
        self.assertFalse(commands.karaoke_request(commands.plain("disattiva karaoke")))
        self.assertIsNone(commands.karaoke_request(commands.plain("metti la musica di Vasco")))

    def test_voice_toggles_and_states_the_privacy(self):
        speech, _ = asyncio.run(commands.answer("abilità karaoke"))
        self.assertTrue(karaoke.enabled())
        self.assertIn("titolo e artista", speech)
        self.assertNotIn("audio, ", speech)
        speech, _ = asyncio.run(commands.answer("disattiva karaoke"))
        self.assertFalse(karaoke.enabled())
        self.assertIn("disattivato", speech)

    def test_source_is_empty_when_off_or_silent(self):
        store.now_playing = {"title": "T", "artist": "A", "key": "k", "expires": time.time() + 99}
        self.assertEqual(karaoke.source(), {})
        write_env({"NUXIVA_MUSIC_KARAOKE": "1"})
        store.now_playing = {}
        self.assertEqual(karaoke.source(), {})

    def test_source_uses_recognised_lyrics_and_loads_missing_ones(self):
        write_env({"NUXIVA_MUSIC_KARAOKE": "1"})
        now = time.time()
        synced = {"synced": [{"t": 1.0, "text": "ciao"}]}
        store.now_playing = {"title": "T", "artist": "A", "key": "k1", "duration": 100, "started_at": now - 5, "lyrics": synced, "expires": now + 90}
        out = karaoke.source()
        self.assertEqual((out["lyrics_state"], out["lyrics_origin"], out["lyrics"]), ("ready", "lrclib", synced))
        store.now_playing = {"title": "T2", "artist": "A", "key": "k2", "started_at": now, "lyrics": {}, "expires": now + 90}

        async def scenario():
            with mock.patch.object(lyrics, "fetch", mock.AsyncMock(return_value={"plain": "testo"})) as fetch:
                first = karaoke.source()
                await asyncio.sleep(0.05)
                second = karaoke.source()
                return first, second, fetch.await_count
        first, second, calls = asyncio.run(scenario())
        self.assertEqual(first["lyrics_state"], "loading")
        self.assertEqual((second["lyrics_state"], second["lyrics_origin"], calls), ("ready", "lrclib", 1))

    def test_no_online_lookup_when_disabled(self):
        write_env({"NUXIVA_MUSIC_KARAOKE": "1", "NUXIVA_MUSIC_LYRICS": "0"})
        self.addCleanup(lambda: write_env({"NUXIVA_MUSIC_LYRICS": "1"}))
        store.now_playing = {"title": "T3", "artist": "A", "key": "k3", "started_at": time.time(), "expires": time.time() + 90}

        async def scenario():
            with mock.patch.object(lyrics, "fetch", mock.AsyncMock(return_value={"plain": "x"})) as fetch:
                karaoke.source()
                await asyncio.sleep(0.05)
                return karaoke.source(), fetch.await_count
        out, calls = asyncio.run(scenario())
        self.assertEqual((out["lyrics_state"], calls), ("none", 0))


if __name__ == "__main__":
    unittest.main()
