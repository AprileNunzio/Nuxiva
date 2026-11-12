import asyncio
import logging
import time
from collections import deque

import numpy as np


log = logging.getLogger("nuxiva.ear.ingress")
MAX_PCM_BYTES = 32000
MAX_PENDING = 4
MAX_AGE = 0.5


class RealtimeInput:
    def __init__(self, analyze, meter, reset):
        self.analyze = analyze
        self.meter = meter
        self.reset = reset
        self.pending = deque()
        self.ready = asyncio.Event()
        self.task = None
        self.closed = False
        self.discontinuous = False
        self.dropped = 0

    async def feed(self, pcm, analyze=True):
        if self.closed:
            return
        if not isinstance(pcm, bytes) or len(pcm) > MAX_PCM_BYTES or len(pcm) % 2:
            raise ValueError("Invalid PCM packet")
        if not pcm:
            return
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        await self.meter(float(np.sqrt(np.mean(samples * samples))))
        if analyze:
            if len(self.pending) >= MAX_PENDING:
                self.pending.popleft()
                self.dropped += 1
                self.discontinuous = True
            self.pending.append((time.monotonic(), pcm))
            self.ready.set()
            if self.task is None:
                self.task = asyncio.create_task(self.run())
        await asyncio.sleep(0)

    async def run(self):
        try:
            while not self.closed:
                await self.ready.wait()
                while self.pending:
                    at, pcm = self.pending.popleft()
                    if time.monotonic() - at > MAX_AGE:
                        self.dropped += 1
                        self.discontinuous = True
                        continue
                    if self.discontinuous:
                        self.discontinuous = False
                        await self.reset()
                    try:
                        await self.analyze(pcm)
                    except Exception:
                        log.exception("Ear frame analysis failed")
                        await self.reset()
                    await asyncio.sleep(0)
                self.ready.clear()
        except Exception:
            log.exception("Ear analysis worker stopped unexpectedly")
        finally:
            if self.task is asyncio.current_task():
                self.task = None
                self.pending.clear()

    def clear(self):
        self.pending.clear()
        self.discontinuous = True
        if self.task is not None:
            self.task.cancel()
            self.task = None

    def stop(self):
        self.closed = True
        self.pending.clear()
        if self.task is not None:
            self.task.cancel()

    async def close(self):
        self.stop()
        if self.task is not None:
            await asyncio.gather(self.task, return_exceptions=True)
