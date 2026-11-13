import asyncio
import random
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
import music as ear_music
import music_room
from music_room import MusicRoom, PyMusicRoom

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustMusicRoom")
FRAME_MS = 30


def script(seed: int, frames: int) -> list[tuple[int, bool, bool]]:
    rng = random.Random(seed)
    out, music, idle = [], False, True
    for _ in range(frames):
        if rng.random() < 0.004:
            music = not music
        if rng.random() < 0.002:
            idle = not idle
        out.append((rng.randrange(3), music and rng.random() < 0.8, idle))
    return out


def replay(engine, steps, finish_every: int = 0):
    room = MusicRoom(engine)
    mics = [room.join() for _ in range(3)]
    now, trace = 1_700_000_000.0, []
    for i, (mic, music, idle) in enumerate(steps):
        step = room.feed(mics[mic], music, idle, FRAME_MS, now)
        trace.append((step.playing, step.change, step.probe))
        if step.probe and finish_every:
            room.finish(now, finish_every)
        if i == len(steps) // 2:
            trace.append(("leave", room.leave(mics[2])))
        now += FRAME_MS / 1000
    return trace


class FallbackRoomTest(unittest.TestCase):
    def feed(self, room, mic, music, ms, now, idle=True):
        out = []
        for _ in range(ms // FRAME_MS):
            out.append(room.feed(mic, music, idle, FRAME_MS, now[0]))
            now[0] += FRAME_MS / 1000
        return out

    def test_music_with_vocal_gaps_starts_once_and_probes(self):
        room = MusicRoom(PyMusicRoom())
        mic, now = room.join(), [100.0]
        steps = []
        for i in range(400):
            steps += self.feed(room, mic, i % 10 < 7, FRAME_MS, now)
        self.assertEqual(sum(s.change == "started" for s in steps), 1)
        self.assertEqual(sum(s.probe for s in steps), 1)
        self.assertTrue(room.playing)

    def test_silence_stops_music(self):
        room = MusicRoom(PyMusicRoom())
        mic, now = room.join(), [0.0]
        self.feed(room, mic, True, 9000, now)
        steps = self.feed(room, mic, False, 8100, now)
        self.assertEqual([s.change for s in steps if s.change], ["stopped"])
        self.assertFalse(room.playing)

    def test_conversation_blocks_probe(self):
        room = MusicRoom(PyMusicRoom())
        mic, now = room.join(), [0.0]
        steps = self.feed(room, mic, True, 15000, now, idle=False)
        self.assertFalse(any(s.probe for s in steps))

    def test_unknown_mic_is_harmless(self):
        room = MusicRoom(PyMusicRoom())
        self.assertFalse(room.feed(None, True, True, FRAME_MS, 0.0).probe)
        self.assertEqual(room.leave(None), "")


@unittest.skipUnless(READY, "nuxiva_native non disponibile")
class NativeParityTest(unittest.TestCase):
    def test_random_scripts_match(self):
        for seed in range(6):
            steps = script(seed, 6000)
            for wait in (0, 20, 300):
                with self.subTest(seed=seed, wait=wait):
                    self.assertEqual(replay(NATIVE.RustMusicRoom(), steps, wait), replay(PyMusicRoom(), steps, wait))

    def test_default_engine_is_native(self):
        self.assertTrue(hasattr(MusicRoom().engine, "mic_playing"))
        self.assertNotIsInstance(MusicRoom().engine, PyMusicRoom)


class TapTest(unittest.TestCase):
    def setUp(self):
        self.room = MusicRoom(PyMusicRoom())
        patcher = mock.patch.object(ear_music, "ROOM", self.room)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_tap_probes_with_capture_time_and_reports_end(self):
        calls = []

        def fake_post(url, body, headers):
            calls.append((url, len(body), dict(headers)))
            return {"ok": True, "found": True, "title": "Brano", "next_in": 60}

        async def scenario():
            tap = ear_music.MusicTap()
            frame = np.full(ear_music.FRAME, 0.05, dtype=np.float32)
            now = time.time() - 60
            for _ in range(int(14 / 0.03)):
                tap.feed(frame, 0.05, 0.004, True, now, True)
                now += 0.03
                await asyncio.sleep(0)
            await asyncio.sleep(0.05)
            for _ in range(int(9 / 0.03)):
                tap.feed(frame, 0.0, 0.004, True, now, False)
                now += 0.03
            await asyncio.sleep(0.05)
            tap.close()

        with mock.patch.object(ear_music, "_post", side_effect=fake_post):
            asyncio.run(scenario())
        urls = [c[0] for c in calls]
        self.assertEqual(urls.count(ear_music.MUSIC_URL), 1)
        self.assertEqual(urls.count(ear_music.ENDED_URL), 1)
        probe = next(c for c in calls if c[0] == ear_music.MUSIC_URL)
        self.assertGreater(probe[1], 300_000)
        self.assertIn("X-Nuxiva-Captured-At", probe[2])

    def test_room_module_is_shared(self):
        self.assertIsInstance(music_room.ROOM, MusicRoom)


class WatcherTest(unittest.TestCase):
    def setUp(self):
        from agenti.music import music
        from state import store
        self.music, self.store = music, store
        self.addCleanup(lambda: setattr(store, "now_playing", {}))

    def test_capture_time_is_bounded(self):
        now = 1000.0
        self.assertEqual(self.music.MusicWatcher.capture_time(990.0, now), 990.0)
        self.assertEqual(self.music.MusicWatcher.capture_time(None, now), now - self.music.SAMPLE_WINDOW)
        self.assertEqual(self.music.MusicWatcher.capture_time(2000.0, now), now - self.music.SAMPLE_WINDOW)
        self.assertEqual(self.music.MusicWatcher.capture_time(10.0, now), now - self.music.SAMPLE_WINDOW)

    def test_ended_clears_room_song_but_not_library(self):
        watcher = self.music.MusicWatcher()
        self.store.now_playing = {"title": "X", "key": "1", "expires": time.time() + 100}
        self.assertTrue(watcher.ended())
        self.assertEqual(self.store.now_playing, {})
        self.store.now_playing = {"title": "Y", "source": "library", "expires": time.time() + 100}
        self.assertFalse(watcher.ended())
        self.assertEqual(self.store.now_playing["title"], "Y")

    def test_offset_uses_sample_start(self):
        watcher = self.music.MusicWatcher()
        raw = {"track": {"title": "T", "subtitle": "A", "key": "k1", "sections": []}, "matches": [{"offset": 42.0}]}
        with mock.patch.object(self.music, "enabled", return_value=True), \
                mock.patch.object(self.music, "available", return_value=True), \
                mock.patch.object(watcher, "_recognize", mock.AsyncMock(return_value=raw)), \
                mock.patch.object(watcher, "_itunes", mock.AsyncMock(return_value={"duration": 200.0})), \
                mock.patch.object(watcher, "_bio", mock.AsyncMock(return_value={})), \
                mock.patch.object(self.music.lyrics, "fetch", mock.AsyncMock(return_value={})):
            captured = time.time() - 11
            out = asyncio.run(watcher.handle(b"x" * 2000, captured))
        self.assertTrue(out["found"])
        self.assertAlmostEqual(self.store.now_playing["started_at"], captured - 42.0, places=3)


if __name__ == "__main__":
    unittest.main()
