import asyncio
import json
import logging
import time

import httpx

import native_module
from agenti.sentinel import memory_people, observe, record
from agenti.sentinel.journal import SentinelUnavailable
from agenti.sentinel.memory import memory

log = logging.getLogger("nuxiva.sentinel.watch")
IDLE_MS = 15_000
MAX_SPAN_MS = 600_000
SYNC_EVERY = 600.0
TIMEOUT = 15.0


def enabled() -> bool:
    return record.option("NUXIVA_SENTINEL_MEMORY")


def interval() -> float:
    from agenti.desktop.privacy import number
    return number("NUXIVA_SENTINEL_WATCH_EVERY", 5.0, 2.0, 120.0)


def sources() -> list[dict]:
    from agenti.cameras import live
    return [r for r in live.all_rows() if r["kind"] != "infrared"]


class Watcher:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self.assembler = None
        self.synced: dict[str, float] = {}
        self.stored = 0

    def _ready(self):
        if self.assembler is None:
            cls = native_module.feature("RustSightingAssembler")
            if cls is None:
                raise SentinelUnavailable("sentinel.memory.native.missing")
            self.assembler = cls(IDLE_MS, MAX_SPAN_MS)
        return self.assembler

    def feed(self, rows: list[dict]) -> list[dict]:
        engine = self._ready()
        done = []
        for row in rows:
            try:
                done.extend(json.loads(engine.push(json.dumps(row))))
            except ValueError as exc:
                log.debug("Osservazione scartata: %s", exc)
        done.extend(json.loads(engine.flush(int(self.clock() * 1000))))
        return done

    def store(self, sightings: list[dict]) -> int:
        saved = 0
        for sighting in sightings:
            try:
                memory.add(sighting)
            except ValueError as exc:
                log.warning("Passaggio non salvato: %s", exc)
                continue
            saved += 1
            self._sync(sighting.get("who") or {})
        self.stored += saved
        return saved

    def _sync(self, who: dict) -> None:
        if who.get("type") != "person":
            return
        slug = self._slug_of(who["id"])
        now = self.clock()
        if slug is None or now - self.synced.get(slug, 0.0) < SYNC_EVERY:
            return
        self.synced[slug] = now
        memory_people.sync(slug)

    @staticmethod
    def _slug_of(pseudonym: str) -> str | None:
        from agenti.people import people
        for p in people.all_profiles(light=True):
            if record.pseudonym(p["slug"]) == pseudonym:
                return p["slug"]
        return None

    async def look(self, client: httpx.AsyncClient, source: dict) -> list[dict]:
        from agenti.cameras import live
        from agenti.vision.proxy import VISION_URL
        from state import store
        frame = await live.snapshot_bytes(source)
        if not frame:
            return []
        response = await client.post(f"{VISION_URL}/bodies", params={"source": source["id"]}, content=frame,
                                     headers={"Content-Type": "application/octet-stream"})
        response.raise_for_status()
        faces = observe.identities(store.presence) if source.get("main") else []
        return observe.observations(source, response.json(), int(self.clock() * 1000), faces)

    async def sweep(self, client: httpx.AsyncClient) -> int:
        rows = []
        for source in await asyncio.to_thread(sources):
            try:
                rows.extend(await self.look(client, source))
            except (httpx.HTTPError, ValueError) as exc:
                log.info("Sentinella non vede dalla telecamera %s: %s", source.get("id"), exc)
        finished = await asyncio.to_thread(self.feed, rows)
        return await asyncio.to_thread(self.store, finished) if finished else 0


watcher = Watcher()


async def run() -> None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while True:
            if enabled():
                try:
                    await watcher.sweep(client)
                except SentinelUnavailable:
                    await asyncio.sleep(300)
                except (OSError, ValueError) as exc:
                    log.error("Memoria della Sentinella: giro non riuscito: %s", exc)
            await asyncio.sleep(interval())
