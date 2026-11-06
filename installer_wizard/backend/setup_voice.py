import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE
from setup_face import require_open
from setup_session import session_manager

router = APIRouter()
MAX_BODY = 4096


async def _body(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "JSON non valido")
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON non valido")
    return body


@router.post("/api/setup/mic")
async def setup_mic(request: Request, _: None = Depends(require_open)):
    body = await _body(request)
    try:
        session_manager.put("mic", body)
    except (TypeError, ValueError):
        raise HTTPException(400, "Misura del microfono non valida")
    return JSONResponse({"mic": session_manager.config.get("mic")}, headers=NO_CACHE)


@router.post("/api/setup/assistant")
async def setup_assistant(request: Request, _: None = Depends(require_open)):
    body = await _body(request)
    try:
        session_manager.put("assistant_name", body.get("name"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    import setup_complete
    name = session_manager.config.get("assistant_name") or ""
    return JSONResponse({"assistant_name": name, "wake_word": setup_complete.wake_word(name)}, headers=NO_CACHE)
