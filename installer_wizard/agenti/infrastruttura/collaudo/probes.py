import asyncio
import glob
import json
import math
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import websockets

from agenti.collaudo import emit, hub

VISION = "http://127.0.0.1:8091"
EAR = "ws://127.0.0.1:8093"
TESTS = Path(__file__).resolve().parents[3] / "tests"


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _result(kind: str, outcome: str, corr: str, **fields) -> dict:
    emit.emit("probe", "info" if outcome != "fail" else "warn", kind, src="collaudo", corr=corr, outcome=outcome, **fields)
    return {"kind": kind, "outcome": outcome, **fields}


async def _fetch(url: str, timeout: float) -> tuple[int, bytes]:
    def get() -> tuple[int, bytes]:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read(4 * 1024 * 1024)
    return await asyncio.to_thread(get)


async def _exec(*argv: str, timeout: float = 10.0) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, ""
    return process.returncode or 0, out.decode("utf-8", "replace")


async def services(corr: str) -> dict:
    if shutil.which("systemctl") is None:
        return _result("services", "skip", corr, reason="no_systemd")
    code, out = await _exec("systemctl", "list-units", "--type=service", "--all", "--no-legend", "--plain", "--no-pager", "nuxiva-*")
    rows = [line.split() for line in out.splitlines() if line.strip()]
    inactive = [r[0] for r in rows if len(r) > 3 and r[2] not in ("active", "activating")]
    if code != 0 or not rows:
        return _result("services", "skip", corr, reason="no_units")
    return _result("services", "ok" if not inactive else "fail", corr, units=len(rows), inactive=len(inactive))


async def bus_roundtrip(corr: str) -> dict:
    from nuxiva_bus import nuxiva_bus

    done = asyncio.Event()
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    sub = nuxiva_bus.subscribe("collaudo.ping", lambda _e: loop.call_soon_threadsafe(done.set))
    try:
        nuxiva_bus.publish("collaudo.ping", {"corr": corr}, origin="supervisor")
        await asyncio.wait_for(done.wait(), 2.0)
    except asyncio.TimeoutError:
        return _result("bus_roundtrip", "fail", corr, latency_ms=2000.0)
    finally:
        sub.cancel()
    return _result("bus_roundtrip", "ok", corr, latency_ms=_ms(start))


async def camera_frame(corr: str) -> dict:
    devices = glob.glob("/dev/video*")
    if not devices:
        return _result("camera_frame", "skip", corr, reason="no_device")
    start = time.perf_counter()
    try:
        status, body = await _fetch(f"{VISION}/frame.jpg", 4.0)
    except (OSError, ValueError):
        return _result("camera_frame", "fail", corr, frames=0, latency_ms=_ms(start), devices=len(devices))
    ok = status == 200 and body[:2] == b"\xff\xd8" and len(body) > 2000
    return _result("camera_frame", "ok" if ok else "fail", corr, frames=1 if ok else 0, bytes=len(body), latency_ms=_ms(start), devices=len(devices))


async def microphone_level(corr: str, since_ms: int) -> dict:
    cards = Path("/proc/asound/cards")
    if not cards.exists():
        return _result("microphone_level", "skip", corr, reason="no_audio")
    await asyncio.sleep(1.5)
    events = await asyncio.to_thread(hub.query, {"domain": "ear", "kind_prefix": "level", "from_ms": since_ms, "limit": 400})
    values = [float(e["fields"]["rms"]) for e in events if isinstance(e.get("fields", {}).get("rms"), (int, float))]
    if not values:
        return _result("microphone_level", "fail", corr, samples=0, level_db=-120.0)
    mean = sum(values) / len(values)
    db = round(20 * math.log10(max(mean / 12.0, 1e-6)), 1)
    return _result("microphone_level", "ok", corr, samples=len(values), level_db=db)


async def ear_roundtrip(corr: str) -> dict:
    start = time.perf_counter()
    try:
        async with websockets.connect(EAR, open_timeout=3, max_size=2 ** 20) as socket:
            while True:
                message = json.loads(await asyncio.wait_for(socket.recv(), 3))
                if message.get("type") == "ready":
                    return _result("ear_roundtrip", "ok", corr, latency_ms=_ms(start), voiceprint=bool(message.get("voiceprint")))
    except (OSError, asyncio.TimeoutError, websockets.WebSocketException, ValueError):
        return _result("ear_roundtrip", "fail", corr, latency_ms=_ms(start))


async def sentinel_chain(corr: str) -> dict:
    from agenti.sentinel.journal import day_of, journal

    try:
        info = await asyncio.to_thread(journal.integrity, day_of(time.time()))
    except Exception as exc:
        return _result("sentinel_chain", "fail", corr, error=type(exc).__name__.lower())
    ok = bool(info.get("chain")) and not info.get("torn") and info.get("signed") is not False
    return _result("sentinel_chain", "ok" if ok else "fail", corr, events=int(info.get("count", 0)))


async def collaudo_chain(corr: str) -> dict:
    info = json.loads(await asyncio.to_thread(hub.get().verify))
    if info.get("ok") is None:
        return _result("collaudo_chain", "skip", corr, reason="native_required")
    return _result("collaudo_chain", "ok" if info["ok"] else "fail", corr, segments=info["segments"], lines=info["lines"])


async def mcp_discovery(corr: str) -> dict:
    from agenti.agent import registry
    from agenti.agent.paths import level

    tools = await asyncio.to_thread(lambda: len(registry.available(level())))
    return _result("mcp_discovery", "ok" if tools else "fail", corr, tools=tools)


async def sandbox_exec(corr: str) -> dict:
    from agenti.agent import shell_sandbox

    if shell_sandbox.mode() != "sandbox":
        return _result("sandbox_exec", "skip", corr, reason="mode_" + shell_sandbox.mode())
    start = time.perf_counter()
    try:
        out = await shell_sandbox.run("echo collaudo-ok", 20)
    except Exception as exc:
        return _result("sandbox_exec", "fail", corr, error=type(exc).__name__.lower())
    return _result("sandbox_exec", "ok" if "collaudo-ok" in out else "fail", corr, latency_ms=_ms(start))


async def parity(corr: str) -> dict:
    if not TESTS.is_dir() or not shutil.which(sys.executable):
        return _result("parity", "skip", corr, reason="no_tests")
    code, out = await _exec(sys.executable, "-m", "pytest", "-q", "-x", "-k", "parity", str(TESTS), timeout=300.0)
    if "No module named pytest" in out:
        return _result("parity", "skip", corr, reason="no_pytest")
    match = re.search(r"(\d+) passed", out)
    passed = int(match.group(1)) if match else 0
    failed = 0 if code == 0 else max(1, out.count("FAILED"))
    return _result("parity", "ok" if code == 0 else "fail", corr, passed=passed, failed=failed)
