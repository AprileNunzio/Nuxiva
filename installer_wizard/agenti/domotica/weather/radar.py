import re
import time

import httpx

MAPS_URL = "https://api.rainviewer.com/public/weather-maps.json"
HOST = "https://tilecache.rainviewer.com"
PATH_RE = re.compile(r"^/v2/radar/[A-Za-z0-9_]{1,64}$")
REFRESH = 300
FRAMES = 6
state: dict = {"at": 0.0, "value": None}


def frames(raw: dict) -> dict | None:
    if not isinstance(raw, dict) or raw.get("host") != HOST:
        return None
    past = ((raw.get("radar") or {}).get("past")) or []
    items = [{"time": int(f["time"]), "path": f["path"]} for f in past
             if isinstance(f, dict) and isinstance(f.get("time"), int) and isinstance(f.get("path"), str) and PATH_RE.fullmatch(f["path"])]
    return {"host": HOST, "frames": items[-FRAMES:], "source": "rainviewer.com"} if items else None


async def latest() -> dict | None:
    if time.time() - state["at"] < REFRESH:
        return state["value"]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(MAPS_URL)
            response.raise_for_status()
            value = frames(response.json())
    except (httpx.HTTPError, ValueError):
        value = state["value"]
    state.update(at=time.time(), value=value)
    return value
