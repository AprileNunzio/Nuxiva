import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from access import require_admin, require_display
from state import store as state_store
from features.stage import director, particles, show
from features.stage.service import CLIENT, stage
from features.stage.store import DIGEST, store

public_routes = APIRouter()
admin_routes = APIRouter()
MAX_BODY = 16 * 1024


async def _body(request: Request, limit: int = MAX_BODY) -> dict:
    raw = await request.body()
    if len(raw) > limit:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "JSON non valido")
    if not isinstance(body, dict):
        raise HTTPException(400, "Corpo richiesta non valido")
    return body


def _settings() -> dict:
    try:
        from system_api import get_display_settings
        return get_display_settings()
    except Exception:
        return {}


@public_routes.post("/api/stage/plan")
async def stage_plan(request: Request):
    require_display(request, "Solo dal display")
    body = await _body(request)
    client = str(body.get("client") or "")
    if not CLIENT.match(client):
        raise HTTPException(400, "Client non valido")
    intents = {str(i.get("id")) for i in (state_store.desk or []) if isinstance(i, dict) and i.get("intent")}
    return stage.plan(client, body.get("context"), _settings(), intents)


@public_routes.post("/api/stage/feedback")
async def stage_feedback(request: Request):
    require_display(request, "Solo dal display")
    body = await _body(request)
    if not isinstance(body.get("wanted"), bool):
        raise HTTPException(400, "Valore non valido")
    try:
        weight = stage.feedback(str(body.get("client") or ""), str(body.get("surface") or ""), body["wanted"])
    except ValueError:
        raise HTTPException(400, "Superficie sconosciuta")
    except KeyError:
        raise HTTPException(409, "Nessun piano per questo display")
    return {"ok": True, "weight": weight}


@public_routes.get("/api/particles/blob/{digest}")
async def particle_blob(digest: str, request: Request):
    require_display(request, "Solo dal display")
    if not DIGEST.match(digest):
        raise HTTPException(400, "Impronta non valida")
    blob = store.blob(digest)
    if blob is None:
        raise HTTPException(404, "Animazione non trovata")
    return Response(blob, media_type="application/octet-stream",
                    headers={"Cache-Control": "private, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff",
                             "Content-Security-Policy": "default-src 'none'"})


@admin_routes.get("/api/stage/state")
async def stage_state(_: str = Depends(require_admin)):
    return {"engine": director.native.ENGINE, "clients": stage.active(), "particles": show.current(),
            "library": store.listing()[:200]}


@admin_routes.post("/api/particles/show")
async def particle_show(request: Request, _: str = Depends(require_admin)):
    body = await _body(request, 64 * 1024)
    concept = str(body.get("concept") or "")[:120]
    spec = body.get("spec")
    try:
        entry = await show.materialize(concept, spec if isinstance(spec, dict) else None)
    except particles.ParticleError as exc:
        raise HTTPException(400, str(exc))
    try:
        ttl = float(body.get("seconds", show.SHOW_SECONDS))
    except (TypeError, ValueError):
        raise HTTPException(400, "Durata non valida")
    return {"ok": True, "showing": show.present(entry, ttl)}


@admin_routes.post("/api/particles/clear")
async def particle_clear(_: str = Depends(require_admin)):
    show.clear()
    return {"ok": True}
