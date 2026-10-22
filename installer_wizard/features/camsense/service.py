import asyncio
import logging
import time

from config import env_get
from state import store as system_store

from features.camsense import classifier, imaging
from features.camsense.model import SenseError, label_of, region, slug
from features.camsense.store import sensors

log = logging.getLogger("nuxiva.camsense")
CONFIRM = 3
LOST_AFTER = 5
DEFAULT_SECONDS = 10
MIN_SECONDS, MAX_SECONDS = 2, 300
SAFE_TOPIC = "camsense.state."


def enabled() -> bool:
    return env_get("NUXIVA_CAMSENSE", "1") != "0"


def period() -> int:
    try:
        return max(MIN_SECONDS, min(MAX_SECONDS, int(env_get("NUXIVA_CAMSENSE_SECONDS", str(DEFAULT_SECONDS)))))
    except ValueError:
        return DEFAULT_SECONDS


def view(row: dict) -> dict:
    samples = {label: len(rows) for label, rows in row["samples"].items()}
    return {**{k: v for k, v in row.items() if k != "samples"}, "samples": samples, "quality": classifier.quality(row["samples"])}


def cameras() -> list[dict]:
    from features.cameras import live
    return [{"id": r["id"], "name": r["name"], "kind": r["kind"]} for r in live.listing()]


async def frame(camera_id: str) -> bytes:
    from features.cameras import live
    source = live.find(camera_id)
    if source is None:
        raise SenseError("camera_unknown", 404)
    data = await live.snapshot_bytes(source)
    if not data:
        raise SenseError("frame_unavailable", 502)
    return data


def create(name: str, camera: str, area) -> dict:
    from features.cameras import live
    if live.find(str(camera)) is None:
        raise SenseError("camera_unknown", 404)
    return view(sensors.create(slug(name), str(name).strip()[:60], str(camera), region(area)))


def retarget(sensor_id: str, name: str, area) -> dict:
    def change(row: dict) -> None:
        if name:
            row["name"] = str(name).strip()[:60]
        if area is not None:
            row["region"] = region(area)
            row["samples"], row["state"], row["since"] = {}, "", 0.0
            row["pending"] = {"label": "", "count": 0}
    return view(sensors.update(sensor_id, change))


async def learn(sensor_id: str, label: str) -> dict:
    row = sensors.get(sensor_id)
    vector = imaging.vector(await frame(row["camera"]), row["region"])
    return view(sensors.add_sample(sensor_id, label_of(label), vector))


def forget(sensor_id: str, label: str) -> dict:
    def change(row: dict) -> None:
        if row["samples"].pop(label_of(label), None) is None:
            raise SenseError("not_found", 404)
        row["state"], row["pending"] = "", {"label": "", "count": 0}
    return view(sensors.update(sensor_id, change))


async def preview(sensor_id: str) -> bytes:
    row = sensors.get(sensor_id)
    return imaging.outline(await frame(row["camera"]), row["region"])


def settle(row: dict, verdict: classifier.Verdict, now: float) -> str | None:
    row.update(confidence=round(verdict.confidence, 3), reason=verdict.reason, checked=now, misses=0)
    if not verdict.label or verdict.label == row["state"]:
        row["pending"] = {"label": "", "count": 0}
        return None
    pending = row["pending"]
    count = pending["count"] + 1 if pending["label"] == verdict.label else 1
    row["pending"] = {"label": verdict.label, "count": count}
    if count < CONFIRM and row["state"]:
        return None
    previous, row["state"], row["since"] = row["state"], verdict.label, now
    row["pending"] = {"label": "", "count": 0}
    return previous


def announce(row: dict, previous: str) -> None:
    text = f"{row['name']}: {row['state']}" + (f" (prima: {previous})" if previous else "")
    system_store.event("INFO", f"Sensore {text}", "camsense")
    try:
        from features.cameras import events
        events.add("sensor", row["id"], row["name"], text)
    except ImportError as exc:
        log.warning("Evento del sensore non registrato: %s", exc)
    try:
        from nuxiva_bus import BusError, nuxiva_bus
        nuxiva_bus.publish(SAFE_TOPIC + row["id"].replace("-", "_"), {"id": row["id"], "name": row["name"], "state": row["state"],
                                                                      "previous": previous, "confidence": row["confidence"]}, origin="camsense", retain=True)
    except (ImportError, BusError) as exc:
        log.warning("Stato del sensore non pubblicato: %s", exc)


def read(row: dict, jpeg: bytes) -> classifier.Verdict:
    return classifier.classify(row["samples"], imaging.vector(jpeg, row["region"]))


def apply(sensor_id: str, verdict: classifier.Verdict) -> dict:
    outcome: list[str | None] = []
    updated = sensors.update(sensor_id, lambda row: outcome.append(settle(row, verdict, time.time())))
    if outcome[0] is not None:
        announce(updated, outcome[0])
    return updated


async def check(sensor_id: str) -> dict:
    row = sensors.get(sensor_id)
    return view(apply(sensor_id, read(row, await frame(row["camera"]))))


def lose(sensor_id: str, reason: str) -> None:
    def change(row: dict) -> None:
        row["misses"] = row.get("misses", 0) + 1
        row["checked"] = time.time()
        if row["misses"] >= LOST_AFTER:
            row["reason"] = reason
            row["confidence"] = 0.0
    try:
        sensors.update(sensor_id, change)
    except SenseError as exc:
        log.info("Sensore %s non più presente: %s", sensor_id, exc.code)


async def tick() -> None:
    rows = sensors.all()
    cache: dict[str, bytes | None] = {}
    for sensor_id, row in rows.items():
        if len([k for k, v in row["samples"].items() if v]) < 2:
            continue
        camera = row["camera"]
        if camera not in cache:
            try:
                cache[camera] = await frame(camera)
            except SenseError:
                cache[camera] = None
        if cache[camera] is None:
            lose(sensor_id, "camera_offline")
            continue
        try:
            verdict = read(row, cache[camera])
        except SenseError:
            lose(sensor_id, "frame_invalid")
            continue
        apply(sensor_id, verdict)


async def run() -> None:
    while True:
        if enabled():
            try:
                await tick()
            except Exception:
                log.exception("Ciclo dei sensori interrotto")
        await asyncio.sleep(period())
