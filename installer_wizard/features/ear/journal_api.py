import json
import time

from fastapi import APIRouter, HTTPException, Request, Response

from access import require_admin
from config import STATE_DIR
from features.ear.journal import ID, journal
from features.people import people
from state import store

routes = APIRouter()
LINK_FILE = STATE_DIR / "ear_link.json"
FIELD_MAX = 2000


def live_status() -> dict:
    try:
        link = json.loads(LINK_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"available": False}
    live = link.get("live") if isinstance(link.get("live"), dict) else {}
    fresh = time.time() - float(link.get("at") or 0) < 30
    return {"available": fresh, **{k: live.get(k) for k in ("mode", "active", "reason", "interval", "decode_ms", "load")}}


def household() -> list[dict]:
    return [{"slug": p["slug"], "name": people.display_name(p)} for p in people.all_profiles(light=True)]


def entry_id(value: str) -> str:
    if not ID.match(value):
        raise HTTPException(400, "Identificativo non valido")
    return value


def number(request: Request, key: str, default: float) -> float:
    try:
        return float(request.query_params.get(key, default))
    except ValueError:
        raise HTTPException(400, f"Valore non valido: {key}")


@routes.get("/api/ear/journal")
async def journal_list(request: Request):
    require_admin(request)
    query = request.query_params
    items = journal.entries(limit=int(number(request, "limit", 40)), before=number(request, "before", 0.0),
                            kind=query.get("kind", "")[:10], speaker=query.get("speaker", "")[:41],
                            verdict=query.get("verdict", "")[:10], query=query.get("q", "")[:80])
    return {"items": items, "stats": journal.stats(), "live": live_status(), "people": household()}


@routes.get("/api/ear/journal/{item}/audio")
async def journal_audio(item: str, request: Request):
    require_admin(request)
    wav = journal.audio(entry_id(item))
    if wav is None:
        raise HTTPException(404, "Registrazione non disponibile")
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@routes.post("/api/ear/journal/{item}/feedback")
async def journal_feedback(item: str, request: Request):
    require_admin(request)
    body = await request.json()
    verdict = str(body.get("verdict") or "")
    speaker = str(body.get("speaker") or "")[:41]
    if speaker and speaker not in {p["slug"] for p in household()}:
        raise HTTPException(400, "Persona sconosciuta")
    saved = journal.feedback(entry_id(item), verdict, str(body.get("correction") or "")[:FIELD_MAX], speaker,
                             str(body.get("note") or "")[:FIELD_MAX])
    if not saved:
        raise HTTPException(404, "Voce del registro non trovata o verdetto non valido")
    return {"ok": True}


@routes.delete("/api/ear/journal/{item}")
async def journal_delete(item: str, request: Request):
    require_admin(request)
    if not journal.delete(entry_id(item)):
        raise HTTPException(404, "Voce del registro non trovata")
    return {"ok": True}


@routes.post("/api/ear/journal/purge")
async def journal_purge(request: Request):
    require_admin(request)
    removed = journal.purge()
    store.event("INFO", f"Registro dell'ascolto svuotato: {removed} voci", "ear")
    return {"ok": True, "removed": removed}
