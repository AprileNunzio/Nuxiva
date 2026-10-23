import json

from fastapi import APIRouter, HTTPException, Request

from access import require_display
from features.games import saves
from features.people import people

public_routes = APIRouter()
BODY_LIMIT = 24576


def _guard(request: Request, slug: str) -> str:
    require_display(request)
    if request.method in ("PUT", "DELETE") and request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "Richiesta non valida")
    if not people.load(slug):
        raise HTTPException(404, "Persona non trovata")
    return people.slugify(slug)


def _id(save_id: str) -> str:
    if save_id != "new" and not saves.SAVE_ID.match(save_id):
        raise HTTPException(404, "Partita non trovata")
    return save_id


@public_routes.get("/api/games/chess/{slug}")
async def chess_list(slug: str, request: Request):
    return {"saves": saves.listing(_guard(request, slug))}


@public_routes.get("/api/games/chess/{slug}/{save_id}")
async def chess_get(slug: str, save_id: str, request: Request):
    row = saves.get(_guard(request, slug), _id(save_id))
    if not row:
        raise HTTPException(404, "Partita non trovata")
    return {**saves.summary(row), "save": row["save"]}


@public_routes.put("/api/games/chess/{slug}/{save_id}")
async def chess_put(slug: str, save_id: str, request: Request):
    who = _guard(request, slug)
    raw = await request.body()
    if len(raw) > BODY_LIMIT:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("Partita non valida")
        return saves.put(who, _id(save_id), body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc))


@public_routes.delete("/api/games/chess/{slug}/{save_id}")
async def chess_delete(slug: str, save_id: str, request: Request):
    if not saves.remove(_guard(request, slug), _id(save_id)):
        raise HTTPException(404, "Partita non trovata")
    return {"ok": True}
