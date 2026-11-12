import logging

from fastapi import APIRouter, HTTPException, Request

from access import require_display
from agenti.desktop import lifecycle

log = logging.getLogger("nuxiva.display.lifecycle")
_last = {"error": ""}
public_routes = APIRouter()
admin_routes = APIRouter()


@public_routes.post("/api/display/lifecycle")
async def lifecycle_report(request: Request):
    require_display(request, "Solo dal display")
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "display.bad_request") from exc
    try:
        return await lifecycle.report(lifecycle.engine, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except lifecycle.EngineRejected as exc:
        raise HTTPException(422, exc.code) from exc
    except lifecycle.EngineUnavailable as exc:
        if _last["error"] != str(exc):
            _last["error"] = str(exc)
            log.warning("Gestore dei widget nuxiva-display non raggiungibile, ciclo di vita solo locale: %s", exc)
        return {"engine": "local", "states": {}, "due": []}
