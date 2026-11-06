import asyncio
import logging
import time

import httpx

from config import env_get
from features.people import faces, people
from features.people.views import FACES
from features.vision.proxy import VISION_URL
from state import store

log = logging.getLogger("nuxiva.people.cameras")
MAX_SIGHTINGS = 20
SYNC_EVERY = 30.0
TIMEOUT = 20.0


def enabled() -> bool:
    return env_get("NUXIVA_OBSERVE_CAMERAS", "1").strip().lower() not in ("0", "off", "no", "false")


def interval() -> float:
    try:
        return max(3.0, min(300.0, float(env_get("NUXIVA_OBSERVE_EVERY", "8"))))
    except ValueError:
        return 8.0


def sources() -> list[dict]:
    from features.cameras import live
    return [r for r in live.all_rows() if r["kind"] != "infrared" and not (r["kind"] == "local" and r["main"])]


def remember(slugs: list[str], source: dict, now: float) -> None:
    label = str(source.get("alias") or source.get("name") or source["id"])[:60]
    for slug in slugs:
        profile = people.load(slug)
        if profile is None:
            continue
        rows = [s for s in profile.get("sightings") or [] if isinstance(s, dict) and s.get("source") != source["id"]]
        rows.append({"source": source["id"], "camera": label, "room": str(source.get("room") or "")[:40], "at": now})
        profile["sightings"] = sorted(rows, key=lambda s: s.get("at", 0))[-MAX_SIGHTINGS:]
        people.save(profile)


async def observe(client: httpx.AsyncClient, source: dict) -> dict:
    from features.cameras import live
    frame = await live.snapshot_bytes(source)
    if not frame:
        return {}
    response = await client.post(f"{VISION_URL}/observe", params={"source": source["id"]}, content=frame,
                                 headers={"Content-Type": "application/octet-stream"})
    response.raise_for_status()
    result = response.json()
    return result if isinstance(result, dict) else {}


async def adopt() -> list[str]:
    created = faces.sync_gallery(FACES) + await faces.sync_vision()
    for slug in created:
        store.event("INFO", f"Volto rilevato aggiunto a Persone: {slug}", "people")
    for pair in await faces.absorb_shadows():
        guest, host = pair.split(">", 1)
        store.event("INFO", f"Doppione automatico {guest} unito a {host}", "people")
    return created


async def sweep(client: httpx.AsyncClient) -> None:
    now = time.time()
    for source in await asyncio.to_thread(sources):
        try:
            result = await observe(client, source)
        except (httpx.HTTPError, ValueError) as exc:
            log.info("Osservazione della telecamera %s non riuscita: %s", source["id"], exc)
            continue
        seen = [*result.get("known", []), *result.get("created", [])]
        if result.get("created"):
            await adopt()
        if seen:
            await asyncio.to_thread(remember, [str(s) for s in seen], source, now)


async def run() -> None:
    last_sync = 0.0
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while True:
            if time.monotonic() - last_sync >= SYNC_EVERY:
                last_sync = time.monotonic()
                await adopt()
            if enabled():
                await sweep(client)
            await asyncio.sleep(interval())
