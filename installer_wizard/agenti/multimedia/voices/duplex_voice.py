import asyncio
import json
import logging
import os
import struct
import time

from agenti.chat import interrupt
from agenti.ear import duplex, speech_stream
from agenti.voices import pcm_stream

log = logging.getLogger("nuxiva.voice.duplex")

MAX_MESSAGE = 8192
MAX_SAY = 4000
MAX_SESSIONS = 16
MAX_PENDING_FRAMES = 4
HEADER = struct.Struct(">II")
PUMP_SECONDS = 0.01
DRAIN_LIMIT_SECONDS = 30.0
_sessions: dict[str, "VoiceSession"] = {}


def enabled() -> bool:
    return os.environ.get("NUXIVA_DUPLEX", "legacy").strip().lower() == "rust"


def now_ms() -> int:
    return int(time.time() * 1000)


class TokenFeed:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()

    def put(self, token: str) -> None:
        self._queue.put_nowait(token)

    def close(self) -> None:
        self._queue.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        token = await self._queue.get()
        if token is None:
            raise StopAsyncIteration
        return token


class VoiceSession:
    def __init__(self, device: str, send_json, send_bytes, synthesize, clock=now_ms) -> None:
        self.device = device
        self._send_json, self._send_bytes, self._synth, self._clock = send_json, send_bytes, synthesize, clock
        self.engine = duplex.build("", clock())
        self.epoch = 0
        self.feed: TokenFeed | None = None
        self.task: asyncio.Task | None = None
        self.chunks: dict[int, str] = {}
        self.played: set[int] = set()
        self.full_text = ""
        self.counts = {"replies": 0, "chunks": 0, "cuts": 0, "stale": 0}
        self.began_ms = 0
        self.first_noted = False
        self.pcm = False
        self.pacer = None
        self.pump: asyncio.Task | None = None

    def _state(self) -> str:
        return json.loads(self.engine.snapshot())["state"]

    def _open(self) -> int:
        now = self._clock()
        self.engine.tick(now)
        for step in {"idle": (), "listening": ("voice_end",), "thinking": (), "interrupted": ("resume", "voice_end"), "speaking": ("reset",)}[self._state()]:
            self.engine.trigger(step, now)
        return self.engine.begin_reply(now)

    async def begin(self) -> TokenFeed:
        await self.stop()
        self.epoch = self._open()
        self.chunks, self.played, self.full_text = {}, set(), ""
        self.feed = TokenFeed()
        flag = self.engine.bind(self.epoch)
        self.counts["replies"] += 1
        self.began_ms, self.first_noted = self._clock(), False
        self.task = asyncio.create_task(self._run(self.epoch, flag, self.feed))
        if self.pcm:
            self.pacer = self.pacer or pcm_stream.build()
            self.pump = asyncio.create_task(self._pump(self.epoch))
        await self._send_json({"type": "reply_start", "gen": self.epoch})
        return self.feed

    async def _speak(self, epoch: int, chunk: str) -> None:
        wav = await self._synth(chunk)
        if not self.engine.is_live(epoch) or epoch != self.epoch:
            self.counts["stale"] += 1
            return
        seq = self.engine.next_seq(epoch)
        self.chunks[seq] = chunk
        self.counts["chunks"] += 1
        if self.pcm:
            try:
                rate, frames, ms = self.pacer.push_wav(epoch, seq, wav)
            except ValueError as exc:
                log.warning("Blocco audio scartato: %s", exc)
                self.chunks.pop(seq, None)
                self.counts["chunks"] -= 1
                return
            await self._send_json({"type": "chunk", "gen": epoch, "seq": seq, "text": chunk, "pcm": True, "rate": rate, "frames": frames, "ms": ms})
        else:
            await self._send_json({"type": "chunk", "gen": epoch, "seq": seq, "text": chunk})
            await self._send_bytes(HEADER.pack(epoch, seq) + wav)
        if not self.first_noted:
            self.first_noted = True
            self._note_first_audio()

    def _note_first_audio(self) -> None:
        from agenti.collaudo.emit import emit

        emit("probe", "info", "voice_first_audio", src="duplex", outcome="ok", latency_ms=max(0, self._clock() - self.began_ms))

    async def _pump(self, epoch: int) -> None:
        pacer = self.pacer
        while epoch == self.epoch and self.engine.is_live(epoch):
            for frame in pacer.poll(self._clock(), epoch):
                if epoch != self.epoch or not self.engine.is_live(epoch):
                    return
                await self._send_bytes(frame)
            await asyncio.sleep(PUMP_SECONDS)

    async def _drain(self, flag) -> None:
        deadline = self._clock() + int(DRAIN_LIMIT_SECONDS * 1000)
        while not flag.is_cancelled() and self._clock() < deadline and (self.pacer.queued() or self.pacer.in_flight_ms(self._clock())):
            await asyncio.sleep(PUMP_SECONDS)

    async def _run(self, epoch: int, flag, feed: TokenFeed) -> None:
        async def tokens():
            async for token in feed:
                self.full_text += token
                yield token

        async def speak(chunk: str) -> None:
            while len(self.chunks) - len(self.played) >= MAX_PENDING_FRAMES and not flag.is_cancelled():
                await asyncio.sleep(0.02)
            if not flag.is_cancelled():
                await self._speak(epoch, chunk)

        try:
            await speech_stream.stream_reply(tokens(), speak, flag)
            if self.pcm and self.pacer is not None:
                await self._drain(flag)
            if not flag.is_cancelled() and self.engine.is_live(epoch):
                self.engine.finish(epoch, self._clock())
                await self._send_json({"type": "reply_end", "gen": epoch})
        except (OSError, RuntimeError, ValueError) as exc:
            log.error("Risposta vocale interrotta da un errore: %s", exc)
            await self._send_json({"type": "error", "code": "duplex.reply_failed"})

    def acknowledge(self, epoch: int, seq: int) -> None:
        if epoch == self.epoch and seq in self.chunks and seq not in self.played:
            self.played.add(seq)
            try:
                self.engine.mark_spoken(epoch, len(self.chunks[seq]))
            except ValueError:
                return

    async def cut(self) -> dict | None:
        if self.task is None or self._state() != "speaking":
            return None
        report = json.loads(self.engine.cut(0, self._clock()))
        dropped = self.pacer.cancel() if self.pacer is not None else (0, 0)
        self.counts["cuts"] += 1
        spoken = " ".join(self.chunks[s] for s in sorted(self.played))
        unheard = [self.chunks[s] for s in sorted(self.chunks) if s not in self.played]
        rest = self.full_text
        for seq in sorted(self.chunks):
            rest = rest.replace(self.chunks[seq], "", 1)
        interrupt.remember(self.device, spoken, " ".join([*unheard, rest.strip()]).strip())
        await self.stop()
        await self._send_json({"type": "cut", "gen": report["gen"], "dropped_ms": dropped[1]})
        return report

    async def stop(self) -> None:
        feed, task, pump = self.feed, self.task, self.pump
        self.feed = self.task = self.pump = None
        if self.pacer is not None:
            self.pacer.cancel()
        if pump is not None and not pump.done():
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)
        if feed is not None:
            feed.close()
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def handle(self, message: str) -> None:
        if len(message) > MAX_MESSAGE:
            return
        try:
            doc = json.loads(message)
        except ValueError:
            return
        kind = doc.get("type") if isinstance(doc, dict) else None
        if kind == "hello":
            self.pcm = doc.get("pcm") is True and doc.get("version", 1) == 1
        elif kind == "say":
            text = str(doc.get("text") or "")[:MAX_SAY]
            if text.strip():
                feed = await self.begin()
                feed.put(text)
                feed.close()
        elif kind == "cut":
            await self.cut()
        elif kind == "played" and isinstance(doc.get("gen"), int) and isinstance(doc.get("seq"), int):
            self.acknowledge(doc["gen"], doc["seq"])


def attach(device: str, session: VoiceSession) -> bool:
    if len(_sessions) >= MAX_SESSIONS and device not in _sessions:
        return False
    _sessions[device] = session
    return True


def detach(device: str, session: VoiceSession) -> None:
    if _sessions.get(device) is session:
        del _sessions[device]


def session_for(device: str) -> "VoiceSession | None":
    return _sessions.get(device)
