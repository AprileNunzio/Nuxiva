from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from access import NO_CACHE, require_admin, require_display
from features.diorama import catalog, export, learned, learning, reference, service, spec as S, store

admin_routes = APIRouter(prefix="/api/diorama", tags=["Diorama"])
public_routes = APIRouter(tags=["Diorama"])
STAGE_PAGE = Path(__file__).resolve().parents[3] / "client_web" / "dist" / "index.html"


class CreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=3, max_length=600)


class RefineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=2, max_length=400)


class ItemIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str = Field(min_length=1, max_length=40)


class LookIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    light: str | None = None
    lens: str | None = None
    blur: float | None = None
    mist: float | None = None
    angle: float | None = None
    orbit: bool | None = None


class BaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    w: float | None = None
    d: float | None = None
    depth: float | None = None
    soil: str | None = None
    top: str | None = None


def _record(did: str) -> dict:
    try:
        return store.load(did)
    except KeyError:
        raise HTTPException(404, "diorama_unknown")


def _save(record: dict) -> dict:
    record["revision"] += 1
    store.save(record)
    export.save(record["id"])
    return record


@admin_routes.get("/catalog/search")
async def search_catalog(q: str = Query("", max_length=120), _: str = Depends(require_admin)):
    return JSONResponse({"results": reference.search(q)}, headers=NO_CACHE)


@admin_routes.get("/catalog/kind/{kind}")
async def get_kind(kind: str, _: str = Depends(require_admin)):
    row = reference.describe(kind) if learned.ID_RE.fullmatch(kind) or kind in catalog.BY_ID else None
    if not row:
        raise HTTPException(404, "kind_unknown")
    return JSONResponse(row, headers=NO_CACHE)


@admin_routes.get("/catalog")
async def get_catalog(_: str = Depends(require_admin)):
    return JSONResponse(catalog.public(), headers=NO_CACHE)


@admin_routes.get("")
async def listing(_: str = Depends(require_admin)):
    return JSONResponse({"items": store.listing()}, headers=NO_CACHE)


@admin_routes.post("")
async def create(body: CreateIn, _: str = Depends(require_admin)):
    try:
        record = service.create(body.prompt)
    except S.SpecError as exc:
        raise HTTPException(400, str(exc))
    return JSONResponse({"id": record["id"]}, headers=NO_CACHE)


def _with_recipes(record: dict) -> dict:
    kinds = {i["kind"] for i in record["items"]}
    return {**record, "job": service.status(record["id"]), "recipes": learned.recipes_for(kinds)}


@admin_routes.get("/learned")
async def learned_list(_: str = Depends(require_admin)):
    rows = [{"id": k, "label": v["label"], "hint": v["hint"], "created": v["created"], "parts": len(v["recipe"]["parts"])} for k, v in learned.load().items()]
    return JSONResponse({"items": rows, "enabled": learning.enabled()}, headers=NO_CACHE)


@admin_routes.post("/learned/study")
async def learned_study(_: str = Depends(require_admin)):
    if learning.state["running"]:
        raise HTTPException(409, "busy")
    from tasks import background
    background(learning.study_once())
    return {"ok": True}


@admin_routes.delete("/learned/{kind}")
async def learned_delete(kind: str, _: str = Depends(require_admin)):
    if not learned.ID_RE.fullmatch(kind) or not learned.remove(kind):
        raise HTTPException(404, "learned_unknown")
    return {"ok": True}


@admin_routes.get("/{did}")
async def get_one(did: str, _: str = Depends(require_admin)):
    return JSONResponse(_with_recipes(_record(did)), headers=NO_CACHE)


@admin_routes.delete("/{did}")
async def delete(did: str, _: str = Depends(require_admin)):
    _record(did)
    store.remove(did)
    service.jobs.pop(did, None)
    return {"ok": True}


@admin_routes.post("/{did}/refine")
async def refine(did: str, body: RefineIn, _: str = Depends(require_admin)):
    _record(did)
    try:
        return await service.refine(did, body.instruction)
    except S.SpecError as exc:
        raise HTTPException(409 if str(exc) == "busy" else 422, str(exc))


@admin_routes.post("/{did}/items")
async def add_item(did: str, body: ItemIn, _: str = Depends(require_admin)):
    record = _record(did)
    if len(record["items"]) >= S.MAX_ITEMS:
        raise HTTPException(400, "items_full")
    try:
        fresh = S.clean_item(body.model_dump())
    except S.SpecError as exc:
        raise HTTPException(400, str(exc))
    record["items"].append(fresh)
    _save(record)
    return fresh


@admin_routes.put("/{did}/items/{iid}")
async def update_item(did: str, iid: str, body: ItemIn, _: str = Depends(require_admin)):
    record = _record(did)
    for index, old in enumerate(record["items"]):
        if old["id"] == iid:
            patch = body.model_dump()
            params = {**old["params"], **(patch.get("params") if isinstance(patch.get("params"), dict) else {})}
            record["items"][index] = S.clean_item({**old, **patch, "params": params, "kind": old["kind"]}, iid)
            _save(record)
            return record["items"][index]
    raise HTTPException(404, "item_unknown")


@admin_routes.delete("/{did}/items/{iid}")
async def delete_item(did: str, iid: str, _: str = Depends(require_admin)):
    record = _record(did)
    kept = [i for i in record["items"] if i["id"] != iid]
    if len(kept) == len(record["items"]):
        raise HTTPException(404, "item_unknown")
    record["items"] = kept
    _save(record)
    return {"ok": True}


@admin_routes.put("/{did}/look")
async def set_look(did: str, body: LookIn, _: str = Depends(require_admin)):
    record = _record(did)
    record["look"] = S.clean_look({**record["look"], **body.model_dump(exclude_none=True)})
    return _save(record)["look"]


@admin_routes.put("/{did}/base")
async def set_base(did: str, body: BaseIn, _: str = Depends(require_admin)):
    record = _record(did)
    record["base"] = S.clean_base({**record["base"], **body.model_dump(exclude_none=True)})
    return _save(record)["base"]


@public_routes.get("/diorama-stage", include_in_schema=False)
async def stage_page(request: Request):
    require_display(request, "display_only")
    if not STAGE_PAGE.is_file():
        raise HTTPException(404, "stage_unavailable")
    return FileResponse(str(STAGE_PAGE), headers={"Cache-Control": "no-cache"})


@public_routes.get("/api/diorama/{did}/display")
async def display_state(did: str, request: Request):
    require_display(request, "display_only")
    return JSONResponse(_with_recipes(_record(did)), headers=NO_CACHE)
