import asyncio
import re
import time

from features.music import dlna
from features.music.outputs import outputs
from features.musicstudio import library

SONOS_ID = re.compile(r"^RINCON[A-Za-z0-9_-]{6,50}$")
DEFAULT_LATENCY = {"cast": 1.4, "dlna": 0.3, "sonos": 0.3, "display": 0.6}
MAX_DEVICES = 24
latency: dict[str, float] = {}
GROUP_KINDS = ("sonos",)


def estimate(device: dict) -> float:
    return latency.get(device["id"], DEFAULT_LATENCY.get(device.get("kind", "dlna"), 0.4))


def learn(device: dict, seconds: float) -> None:
    previous = latency.get(device["id"], seconds)
    latency[device["id"]] = round(previous * 0.6 + seconds * 0.4, 3)


async def listing(refresh: bool = False) -> list[dict]:
    return await outputs.refresh(refresh)


def pick(requested: list[str], everyone: bool) -> list[dict]:
    if everyone:
        chosen = list(outputs.devices.values())
    else:
        chosen = [outputs.device(d) for d in dict.fromkeys(requested)]
    if not chosen:
        raise ValueError("no_devices")
    return chosen[:MAX_DEVICES]


async def _group_sonos(rooms: list[dict], track_id: int, user: str, base: str) -> list[dict]:
    leader, followers = rooms[0], rooms[1:]
    started = await outputs.start(leader["id"], user, [track_id], 0, 0.0, base)
    joined = []
    for room in followers:
        try:
            await dlna.call(room, "avt", "SetAVTransportURI", {"CurrentURI": f"x-rincon:{leader['uuid']}", "CurrentURIMetaData": ""})
            joined.append(room["id"])
        except RuntimeError:
            continue
    return [{"device": leader["id"], "role": "leader", "state": started["state"]}] + [{"device": i, "role": "follower", "state": "playing"} for i in joined]


async def _timed(device: dict, track_id: int, user: str, base: str, delay: float) -> dict:
    await asyncio.sleep(max(0.0, delay))
    began = time.monotonic()
    view = await outputs.start(device["id"], user, [track_id], 0, 0.0, base)
    learn(device, time.monotonic() - began)
    return {"device": device["id"], "role": "sync", "state": view["state"]}


async def cast(pid: str, requested: list[str], everyone: bool, user: str, base: str) -> list[dict]:
    track_id = await asyncio.to_thread(library.ensure_indexed, pid)
    if track_id is None:
        raise LookupError("not_rendered")
    chosen = pick(requested, everyone)
    sonos = [d for d in chosen if d.get("kind") in GROUP_KINDS and SONOS_ID.fullmatch(d.get("uuid", ""))]
    others = [d for d in chosen if d not in sonos]
    jobs = []
    if sonos:
        jobs.append(_group_sonos(sonos, track_id, user, base))
    if others:
        slowest = max(estimate(d) for d in others + sonos[:1])
        jobs += [_timed(d, track_id, user, base, slowest - estimate(d)) for d in others]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    rows = []
    for item in results:
        if isinstance(item, list):
            rows += item
        elif isinstance(item, dict):
            rows.append(item)
        else:
            rows.append({"device": "", "role": "error", "state": "error", "error": str(item)[:120]})
    return rows


async def stop(requested: list[str], everyone: bool, base: str) -> int:
    chosen = pick(requested, everyone)
    done = await asyncio.gather(*(outputs.control(d["id"], "stop", 0.0, base) for d in chosen if d["id"] in outputs.sessions), return_exceptions=True)
    return sum(1 for r in done if not isinstance(r, Exception))
