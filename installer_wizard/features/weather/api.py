import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from access import NO_CACHE, require_admin
from features.weather import places, provider, settings

admin_routes = APIRouter(prefix="/api/weather", tags=["Weather"])
ID_RE = re.compile(r"^[0-9a-f]{8}$")


class PlaceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    detail: str = Field(default="", max_length=90)
    default: bool = False


class RenameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


def _known(place_id: str) -> str:
    if not ID_RE.fullmatch(place_id):
        raise HTTPException(404, "place_unknown")
    return place_id


async def _current_place() -> dict | None:
    chosen = places.default()
    if chosen:
        return chosen
    from features.location.locator import locator
    here = await locator.current()
    if here.get("lat") is None:
        return None
    return {"id": "", "name": here.get("name") or "—", "detail": "", "lat": float(here["lat"]), "lon": float(here["lon"])}


@admin_routes.get("/overview")
async def overview(place: str = "", _: str = Depends(require_admin)):
    data = places.load()
    chosen = places.find(_known(place)) if place else await _current_place()
    body = {"places": data["places"], "default": data["default"], "settings": settings.current(), "report": None, "error": ""}
    if chosen is None:
        body["error"] = "no_location"
    else:
        try:
            body["report"] = await provider.report(chosen)
        except provider.WeatherUnavailable:
            body["error"] = "unavailable"
    return JSONResponse(body, headers=NO_CACHE)


@admin_routes.get("/search")
async def search(q: str = "", _: str = Depends(require_admin)):
    from features.location.locator import search as find
    if not 2 <= len(q.strip()) <= 80:
        raise HTTPException(422, "query_invalid")
    try:
        found = await find(q.strip(), 8)
    except Exception as exc:
        raise HTTPException(502, "search_unavailable") from exc
    return JSONResponse({"items": found}, headers=NO_CACHE)


@admin_routes.post("/places", status_code=201)
async def add_place(body: PlaceIn, _: str = Depends(require_admin)):
    try:
        return JSONResponse(places.add(body.name, body.lat, body.lon, body.detail, body.default), status_code=201, headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@admin_routes.post("/places/{place_id}/default")
async def make_default(place_id: str, _: str = Depends(require_admin)):
    if not places.set_default(_known(place_id)):
        raise HTTPException(404, "place_unknown")
    return {"ok": True}


@admin_routes.patch("/places/{place_id}")
async def rename_place(place_id: str, body: RenameIn, _: str = Depends(require_admin)):
    if not places.rename(_known(place_id), body.name):
        raise HTTPException(404, "place_unknown")
    return {"ok": True}


@admin_routes.delete("/places/{place_id}")
async def delete_place(place_id: str, _: str = Depends(require_admin)):
    if not places.remove(_known(place_id)):
        raise HTTPException(404, "place_unknown")
    return {"ok": True}
