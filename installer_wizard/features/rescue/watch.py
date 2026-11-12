import asyncio
import logging
import time

import httpx

from config import env_get
from features.rescue.coordinator import coordinator

log = logging.getLogger("nuxiva.rescue.watch")
VISION_URL = "http://127.0.0.1:8091"
TICK = 2.0
TIMEOUT = 5.0
KINDS = {"fall", "immobility"}


def enabled() -> bool:
    return env_get("NUXIVA_RESCUE", "1") != "0"


class VisionWatch:
    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self.seq = 0

    def ingest(self, events: list, now: float) -> int:
        fed = 0
        for e in events:
            seq = e.get("seq")
            if not isinstance(seq, int) or seq <= self.seq:
                continue
            self.seq = seq
            if e.get("kind") not in KINDS:
                continue
            at = e.get("at")
            at = float(at) if isinstance(at, (int, float)) and not isinstance(at, bool) and 0 < at <= now + 5 else now
            source = str(e.get("camera") or "vision:main")
            try:
                coordinator.observe(e["kind"], float(e.get("probability", 0.0)), float(e.get("confidence", 0.0)),
                                    source, at=at, now=now)
                fed += 1
            except ValueError as exc:
                log.warning("Segnale visivo di soccorso scartato: %s", exc)
        return fed

    async def poll(self, client: httpx.AsyncClient) -> int:
        response = await client.get(f"{VISION_URL}/posture", params={"since": self.seq})
        response.raise_for_status()
        payload = response.json()
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise ValueError("rescue.watch.payload")
        last = payload.get("last")
        if isinstance(last, int) and last < self.seq:
            self.seq = 0
            return 0
        return self.ingest(events, self.clock())


vision = VisionWatch()


async def run() -> None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while True:
            if enabled():
                try:
                    await vision.poll(client)
                except (httpx.HTTPError, ValueError) as exc:
                    log.debug("Visione non raggiungibile per il soccorso: %s", exc)
                coordinator.update()
            await asyncio.sleep(TICK)
