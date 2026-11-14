import asyncio
import json
import time
import urllib.request

from agenti.collaudo import emit

VISION = "http://127.0.0.1:8091/health"
EVERY = 5.0
state = {"up": None}


def _fetch() -> tuple[dict | None, float]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(VISION, timeout=3) as response:
            body = json.loads(response.read(65536))
    except (OSError, ValueError):
        return None, round((time.perf_counter() - start) * 1000, 1)
    return (body if isinstance(body, dict) else None), round((time.perf_counter() - start) * 1000, 1)


async def run(stop: asyncio.Event) -> None:
    while not stop.is_set():
        body, ms = await asyncio.to_thread(_fetch)
        up = body is not None
        if up:
            emit.emit("vision", "warn" if body.get("error") else "info", "health", src="vision", latency_ms=ms,
                      status=str(body.get("status", ""))[:32].lower(), has_error=bool(body.get("error")),
                      people_n=int(body.get("people_enrolled") or 0), objects=bool(body.get("objects")))
        elif state["up"] is not False:
            emit.emit("vision", "warn", "unreachable", src="vision", latency_ms=ms)
        state["up"] = up
        try:
            await asyncio.wait_for(stop.wait(), EVERY)
        except asyncio.TimeoutError:
            pass
