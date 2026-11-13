import asyncio
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request
import wave

import numpy as np

from music_room import PROBE_MAX_WAIT_MS, ROOM

log = logging.getLogger("nuxiva.ear")

RATE = 16000
FRAME = 480
FRAME_MS = FRAME * 1000 // RATE
MUSIC_URL = f"http://127.0.0.1:{os.environ.get('NUXIVA_ADMIN_PORT', '8080')}/api/internal/music"
ENDED_URL = f"{MUSIC_URL}/ended"
WINDOW = 10.0
RETRY_UNREACHABLE = 600.0
MAX_WAIT = PROBE_MAX_WAIT_MS / 1000
_tasks: set = set()


def _wav(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


def _post(url: str, body: bytes, headers: dict) -> dict:
    req = urllib.request.Request(url, data=body, method="POST", headers={"X-Nuxiva-Request": "1", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _probe(audio: np.ndarray, captured_at: float) -> None:
    try:
        result = await asyncio.to_thread(_post, MUSIC_URL, _wav(audio),
                                         {"Content-Type": "audio/wav", "X-Nuxiva-Captured-At": f"{captured_at:.3f}"})
        wait = min(MAX_WAIT, float(result.get("next_in", 120)))
        if result.get("found"):
            log.info("Musica riconosciuta: %s", result.get("title"))
    except (OSError, urllib.error.URLError, ValueError) as exc:
        log.debug("Riconoscimento musicale non disponibile: %s", exc)
        wait = RETRY_UNREACHABLE
    ROOM.finish(time.time(), wait)


async def _ended() -> None:
    try:
        await asyncio.to_thread(_post, ENDED_URL, b"", {"Content-Type": "application/octet-stream"})
        log.info("Musica terminata")
    except (OSError, urllib.error.URLError, ValueError) as exc:
        log.debug("Fine della musica non comunicata: %s", exc)


class MusicTap:

    def __init__(self) -> None:
        self.ring = np.zeros(RATE * 12, dtype=np.float32)
        self.pos = 0
        self.filled = 0
        self.mic = ROOM.join()

    @property
    def playing(self) -> bool:
        return ROOM.playing

    def _store(self, frame: np.ndarray) -> None:
        ring, n, pos = self.ring, len(frame), self.pos
        if pos + n <= len(ring):
            ring[pos:pos + n] = frame
        else:
            k = len(ring) - pos
            ring[pos:], ring[:n - k] = frame[:k], frame[k:]
        self.pos = (pos + n) % len(ring)
        self.filled = min(len(ring), self.filled + n)

    def feed(self, frame: np.ndarray, rms: float, noise: float, idle: bool, now: float,
             music: bool | None = None) -> None:
        self._store(frame)
        heard = rms > max(noise * 2.0, 0.006) if music is None else music
        step = ROOM.feed(self.mic, heard, idle, FRAME_MS, now)
        if step.change == "stopped":
            _spawn(_ended())
        if not step.probe:
            return
        if self.filled < int(RATE * WINDOW):
            ROOM.finish(now, 1.0)
            return
        audio = np.concatenate([self.ring[self.pos:], self.ring[:self.pos]])[-int(RATE * WINDOW):]
        _spawn(_probe(audio, now - WINDOW))

    def close(self) -> None:
        if ROOM.leave(self.mic) == "stopped":
            _spawn(_ended())
        self.mic = None
