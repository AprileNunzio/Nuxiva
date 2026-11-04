import asyncio
import glob
import os
import platform
import re
import shutil
import time
from pathlib import Path

from features.actions.common import sh

SNAPSHOT_TTL = 5.0
APT_TTL = 600.0
LIVE_LEAGUES = ("ita.1", "uefa.champions", "uefa.europa", "ita.2", "eng.1", "esp.1")
MAX_MATCHES = 10
UNIT = re.compile(r"^[A-Za-z0-9@._:-]+\.(service|socket|mount|timer|target|path|scope|slice|device|swap|automount)$")
_cache: dict[str, tuple[float, object]] = {}
_locks: dict[str, asyncio.Lock] = {}


async def _cached(key: str, ttl: float, producer):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        value = await producer()
        _cache[key] = (time.monotonic(), value)
        return value


def _os_name() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')[:80]
    except OSError:
        return platform.system()
    return platform.system()


def _uptime() -> int:
    try:
        return int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return 0


def _memory() -> dict:
    info: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                info[key] = int(parts[0]) * 1024
    except OSError:
        return {"total": 0, "used": 0}
    total = info.get("MemTotal", 0)
    return {"total": total, "used": max(0, total - info.get("MemAvailable", info.get("MemFree", 0)))}


def _temperature() -> float | None:
    values = []
    for path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            values.append(int(Path(path).read_text().strip()) / 1000.0)
        except (OSError, ValueError):
            continue
    plausible = [v for v in values if 0 < v < 130]
    return round(max(plausible), 1) if plausible else None


async def failed_units() -> list[str] | None:
    if not shutil.which("systemctl"):
        return None
    code, out = await sh("systemctl", "--failed", "--plain", "--no-legend", "--no-pager", timeout=10)
    if code != 0:
        return None
    units = (line.split()[0] for line in out.splitlines() if line.strip())
    return [u for u in units if UNIT.fullmatch(u)][:20]


async def _apt() -> dict | None:
    if not shutil.which("apt"):
        return None
    code, out = await sh("apt", "list", "--upgradable", timeout=60)
    if code != 0:
        return None
    rows = [line for line in out.splitlines() if "/" in line and "[" in line]
    return {"count": len(rows), "security": sum(1 for r in rows if "-security" in r),
            "packages": [r.split("/", 1)[0] for r in rows[:30]]}


async def upgradable() -> dict | None:
    return await _cached("apt", APT_TTL, _apt)


async def _debian() -> dict:
    disk = shutil.disk_usage("/")
    try:
        load = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        load = []
    failed, apt = await asyncio.gather(failed_units(), upgradable())
    return {"kind": "debian", "os": _os_name(), "kernel": platform.release()[:60], "host": platform.node()[:60],
            "uptime_s": _uptime(), "load": load, "cpus": os.cpu_count() or 0, "memory": _memory(),
            "disk": {"total": disk.total, "used": disk.used}, "temperature": _temperature(),
            "failed_units": failed, "updates": apt, "at": time.time()}


async def debian() -> dict:
    return await _cached("debian", SNAPSHOT_TTL, _debian)


async def football() -> dict:
    from features.sports import football as source
    from features.sports.fetch import SportsUnavailable
    results = await asyncio.gather(*(source.scoreboard(code) for code in LIVE_LEAGUES), return_exceptions=True)
    matches, failures = [], 0
    for result in results:
        if isinstance(result, SportsUnavailable):
            failures += 1
            continue
        if isinstance(result, BaseException):
            raise result
        matches.extend(result)
    order = {"in": 0, "pre": 1, "post": 2}
    matches.sort(key=lambda m: (order.get(m["state"], 3), m["start"]))
    return {"kind": "football", "matches": matches[:MAX_MATCHES], "available": failures < len(LIVE_LEAGUES), "at": time.time()}


def activity(expert_id: str) -> dict:
    from features.team.board import board
    key = f"expert:{expert_id}"
    doing = board.current().get(key)
    recent = [m for m in board.messages if m["from"] == key][-8:]
    return {"kind": "activity", "doing": doing, "recent": recent, "at": time.time()}


async def snapshot(kind: str, expert_id: str) -> dict:
    base = activity(expert_id)
    if kind == "debian":
        return {**base, "data": await debian()}
    if kind == "football":
        return {**base, "data": await football()}
    return {**base, "data": None}
