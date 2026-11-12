import asyncio
import re
import secrets
import time
from collections.abc import Awaitable, Callable

import numpy as np

import earconf

RATE = 16000
WINDOW_S = 8.0
FIRST_DELAY = 0.6
MIN_AUDIO_S = 0.7
SPEAKER_AT = (1.4, 4.0)
NORMAL = re.compile(r"[^\w]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return text.split()


def stable_count(previous: list[str], current: list[str]) -> int:
    count = 0
    for before, now in zip(previous, current):
        if NORMAL.sub("", before.lower()) != NORMAL.sub("", now.lower()):
            break
        count += 1
    return count


def speaker_enabled() -> bool:
    return earconf.flag("NUXIVA_EAR_LIVE_SPEAKER", True)


class LiveCaptions:

    def __init__(self, send: Callable[..., Awaitable[None]], governor, decode: Callable[[np.ndarray, str], str],
                 identify: Callable[[np.ndarray], tuple], lock: asyncio.Lock) -> None:
        self.send = send
        self.governor = governor
        self.decode = decode
        self.identify = identify
        self.lock = lock
        self.clear()

    def clear(self) -> None:
        self.utt = ""
        self.seq = 0
        self.words: list[str] = []
        self.text = ""
        self.task: asyncio.Task | None = None
        self.speaker_task: asyncio.Task | None = None
        self.next_at = 0.0
        self.checks = 0
        self.speaker: str | None = None
        self.score = 0.0
        self.known: bool | None = None
        self.addressed = False

    def begin(self, addressed: bool) -> str:
        self.stop()
        self.clear()
        self.utt = secrets.token_hex(4)
        self.addressed = addressed
        self.next_at = time.monotonic() + FIRST_DELAY
        return self.utt

    def stop(self) -> None:
        for task in (self.task, self.speaker_task):
            if task is not None and not task.done():
                task.cancel()

    def end(self) -> dict:
        result = {"utt": self.utt, "text": self.text, "speaker": self.speaker, "score": self.score,
                  "known": self.known, "live": self.seq > 0}
        self.stop()
        self.clear()
        return result

    def tick(self, frames: list, lang: str, addressed: bool) -> None:
        if not self.utt or not frames:
            return
        self.addressed = addressed
        length = len(frames[0]) + sum(len(f) for f in frames[1:])
        if length < MIN_AUDIO_S * RATE:
            return
        self._speaker(frames, length)
        busy = self.task is not None and not self.task.done()
        if busy or time.monotonic() < self.next_at or self.lock.locked() or not self.governor.allowed():
            return
        window = np.concatenate(frames)[-int(WINDOW_S * RATE):]
        self.task = asyncio.create_task(self._partial(self.utt, window, lang))

    def _speaker(self, frames: list, length: int) -> None:
        if not speaker_enabled() or self.checks >= len(SPEAKER_AT) or length < SPEAKER_AT[self.checks] * RATE:
            return
        if self.speaker_task is not None and not self.speaker_task.done():
            return
        self.checks += 1
        self.speaker_task = asyncio.create_task(self._identify(self.utt, np.concatenate(frames)))

    async def _identify(self, utt: str, audio: np.ndarray) -> None:
        slug, score, known = await asyncio.to_thread(self.identify, audio)
        if utt == self.utt:
            self.speaker, self.score, self.known = slug, score, known

    async def _partial(self, utt: str, window: np.ndarray, lang: str) -> None:
        async with self.lock:
            started = time.monotonic()
            text = await asyncio.to_thread(self.decode, window, lang)
            self.governor.record(time.monotonic() - started)
        self.next_at = time.monotonic() + self.governor.interval()
        if utt != self.utt or not text:
            return
        current = tokens(text)
        stable = stable_count(self.words, current)
        self.words, self.text, self.seq = current, text, self.seq + 1
        await self.send(type="partial", utt=utt, seq=self.seq, text=text, stable=stable, speaker=self.speaker,
                        score=round(self.score, 3), known=self.known, addressed=self.addressed)
