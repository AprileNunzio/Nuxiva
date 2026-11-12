import asyncio
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE

router = APIRouter()
GAP_S = 3.0
TIMEOUT_S = 10.0
_gate = {"at": 0.0, "lock": asyncio.Lock()}


def require_open(request: Request) -> None:
    import setup_api
    setup_api.require_setup(request)


async def _probe(provider: str, key: str) -> bool:
    from features.cloud.catalog import BY_ID
    from features.cloud.client import endpoint, headers
    spec = BY_ID[provider]
    entry = {"key": key}
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=False) as client:
        res = await client.get(f"{endpoint(spec, entry)}/models", headers=headers(spec, entry))
    return 200 <= res.status_code < 300


@router.post("/api/setup/cloud/test")
async def setup_cloud_test(request: Request, _: None = Depends(require_open)):
    import setup_api
    try:
        raw = await request.json()
    except ValueError:
        raise HTTPException(400, "Dati non validi")
    if not isinstance(raw, dict):
        raise HTTPException(400, "Dati non validi")
    provider, key = setup_api.cloud_choice(raw)
    lock = _gate["lock"]
    if lock.locked() or time.monotonic() - _gate["at"] < GAP_S:
        raise HTTPException(429, "Attendi qualche secondo prima di riprovare")
    async with lock:
        _gate["at"] = time.monotonic()
        try:
            ok = await _probe(provider, key)
        except httpx.HTTPError:
            ok = False
    return JSONResponse({"ok": ok}, headers=NO_CACHE)
