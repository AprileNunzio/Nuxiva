import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from access import NO_CACHE, require_admin
from features.musicstudio import catalog, imports, lyrics as lyr, schema as S, service, store, voicebank

admin_routes = APIRouter(prefix="/api/musicstudio", tags=["Studio musicale"])
MAX_EXPORT = 160 * 1024 * 1024
MAX_PROJECT_BODY = 3 * 1024 * 1024
ERRORS = {"prompt_short": (400, "prompt_short"), "library_full": (409, "library_full"), "role_invalid": (400, "role_invalid"), "tracks_full": (409, "tracks_full"),
          "lyrics_empty": (409, "lyrics_empty"), "no_sections": (409, "no_sections"), "source_invalid": (400, "source_invalid"),
          "source_unreadable": (422, "source_unreadable"), "converter_missing": (503, "converter_missing")}


class CreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=3, max_length=600)


class LayerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=2, max_length=12)
    instrument: str = Field(default="", max_length=40)


class VocalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(default="", max_length=2400)
    lang: str = Field(default="it", min_length=2, max_length=2)
    voice: str = Field(default="", max_length=60)


class TranslateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lang: str = Field(min_length=2, max_length=2)
    sing: bool = True
    voice: str = Field(default="", max_length=60)


class RevoiceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice: str = Field(max_length=60)
    speed: float | None = Field(default=None, ge=0.6, le=1.6)


class ImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=3, max_length=12)
    path: str = Field(min_length=1, max_length=400)


class WriteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3, max_length=300)
    genre: str = Field(default="pop", max_length=20)
    lang: str = Field(default="it", min_length=2, max_length=2)


def _fail(exc: S.SpecError) -> HTTPException:
    code, detail = ERRORS.get(str(exc), (400, "invalid"))
    return HTTPException(code, detail)


def _project(pid: str) -> dict:
    try:
        return store.load(pid)
    except KeyError:
        raise HTTPException(404, "project_unknown")


def _view(project: dict) -> JSONResponse:
    return JSONResponse({**project, "job": service.status(project["id"])}, headers=NO_CACHE)


@admin_routes.get("/catalog")
async def get_catalog(_: str = Depends(require_admin)):
    return JSONResponse({**catalog.public(), "languages": lyr.LANGUAGES}, headers=NO_CACHE)


@admin_routes.get("/projects")
async def list_projects(_: str = Depends(require_admin)):
    return JSONResponse({"projects": store.listing()}, headers=NO_CACHE)


@admin_routes.post("/projects")
async def create_project(body: CreateIn, _: str = Depends(require_admin)):
    try:
        return _view(service.create(body.prompt))
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.get("/projects/{pid}")
async def get_project(pid: str, _: str = Depends(require_admin)):
    return _view(_project(pid))


@admin_routes.put("/projects/{pid}")
async def put_project(pid: str, request: Request, _: str = Depends(require_admin)):
    current = _project(pid)
    if service.status(pid)["state"] == "building":
        raise HTTPException(409, "busy")
    raw = await request.body()
    if len(raw) > MAX_PROJECT_BODY:
        raise HTTPException(413, "too_large")
    try:
        data = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "invalid")
    project = S.clean_project({**data, "id": pid, "created": current["created"], "revision": current["revision"] + 1}, pid)
    store.save(project)
    return _view(project)


@admin_routes.delete("/projects/{pid}")
async def delete_project(pid: str, _: str = Depends(require_admin)):
    try:
        store.remove(pid)
    except KeyError:
        raise HTTPException(404, "project_unknown")
    service.jobs.pop(pid, None)
    return {"ok": True}


@admin_routes.post("/projects/{pid}/layers")
async def add_layer(pid: str, body: LayerIn, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return _view(service.add_layer(pid, body.role, body.instrument))
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.post("/projects/{pid}/vocals")
async def add_vocals(pid: str, body: VocalIn, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return _view(await service.add_vocals(pid, body.text, body.lang, body.voice))
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.post("/projects/{pid}/translate")
async def translate(pid: str, body: TranslateIn, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return _view(await service.translate(pid, body.lang, body.sing, body.voice))
    except S.SpecError as exc:
        raise _fail(exc)
    except (ValueError, RuntimeError):
        raise HTTPException(503, "brain_unavailable")


@admin_routes.get("/voices")
async def list_voices(lang: str = "it", _: str = Depends(require_admin)):
    return JSONResponse({"voices": await voicebank.voices(lang[:5])}, headers=NO_CACHE)


@admin_routes.post("/projects/{pid}/tracks/{tid}/voice")
async def revoice(pid: str, tid: str, body: RevoiceIn, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return _view(await service.revoice(pid, tid, body.voice, body.speed))
    except KeyError:
        raise HTTPException(404, "track_unknown")
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.get("/sources/{kind}")
async def list_sources(kind: str, _: str = Depends(require_admin)):
    try:
        return JSONResponse({"files": imports.browse(kind)}, headers=NO_CACHE)
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.post("/projects/{pid}/imports")
async def import_audio(pid: str, body: ImportIn, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return _view(await imports.bring(pid, body.source, body.path))
    except S.SpecError as exc:
        raise _fail(exc)


@admin_routes.post("/lyrics")
async def write_lyrics(body: WriteIn, _: str = Depends(require_admin)):
    try:
        return {"text": await lyr.write(body.topic, body.genre if body.genre in catalog.GENRES else "pop", body.lang)}
    except (ValueError, RuntimeError):
        raise HTTPException(503, "brain_unavailable")


@admin_routes.get("/projects/{pid}/assets/{name}")
async def get_asset(pid: str, name: str, _: str = Depends(require_admin)):
    _project(pid)
    try:
        return FileResponse(str(service.asset_path(pid, name)), media_type="audio/wav", headers=NO_CACHE)
    except KeyError:
        raise HTTPException(404, "asset_unknown")


@admin_routes.post("/projects/{pid}/export")
async def export_project(pid: str, request: Request, _: str = Depends(require_admin)):
    from features.musicstudio import exporter
    project = _project(pid)
    declared = int(request.headers.get("content-length") or 0)
    if declared > MAX_EXPORT:
        raise HTTPException(413, "too_large")
    raw = await request.body()
    if len(raw) > MAX_EXPORT or raw[:4] != b"RIFF":
        raise HTTPException(400, "invalid_audio")
    try:
        return exporter.save(project, raw)
    except OSError:
        raise HTTPException(503, "storage")
