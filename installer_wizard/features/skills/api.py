from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from access import require_admin
from features.skills import authoring, catalog
from features.skills.library import library
from state import store

admin_routes = APIRouter()


@admin_routes.get("/api/skills")
async def admin_skills(_: str = Depends(require_admin)):
    return library.listing()


@admin_routes.get("/api/algorithms/catalog")
async def admin_algorithms_catalog(_: str = Depends(require_admin)):
    return catalog.scan()


@admin_routes.post("/api/skills")
async def admin_skill_create(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    try:
        key = await authoring.create(body, str(body.get("probe", "")) if isinstance(body, dict) else "")
    except authoring.AuthoringError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", f"Algoritmo {key} creato da {user}", "skills")
    return {"key": key}


@admin_routes.post("/api/skills/generate")
async def admin_skill_generate(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    try:
        key = await authoring.generate(str(body.get("description", "")) if isinstance(body, dict) else "")
    except authoring.AuthoringError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", f"Algoritmo {key} scritto da Nuxiva su richiesta di {user}", "skills")
    return {"key": key}


@admin_routes.put("/api/skills/{key:path}/code")
async def admin_skill_code_set(key: str, request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    try:
        await authoring.replace_code(key, str(body.get("code", "")) if isinstance(body, dict) else "")
    except KeyError:
        raise HTTPException(404, "Algoritmo sconosciuto")
    except authoring.AuthoringError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", f"Codice dell'algoritmo {key} modificato da {user}", "skills")
    return {"ok": True}


@admin_routes.get("/api/skills/{key:path}/code")
async def admin_skill_code(key: str, _: str = Depends(require_admin)):
    try:
        return PlainTextResponse(library.code(key))
    except KeyError:
        raise HTTPException(404, "Algoritmo sconosciuto")


@admin_routes.post("/api/skills/ask")
async def admin_skill_ask(request: Request, _: str = Depends(require_admin)):
    text = str((await request.json()).get("text", ""))[:500]
    return {"answer": await library.try_answer(text), "needs": library.needs_algorithm(text)}


@admin_routes.post("/api/skills/{key:path}/test")
async def admin_skill_test(key: str, request: Request, _: str = Depends(require_admin)):
    try:
        return await library.test(key, str((await request.json()).get("text", ""))[:500])
    except KeyError:
        raise HTTPException(404, "Algoritmo sconosciuto")


@admin_routes.put("/api/skills/{key:path}")
async def admin_skill_set(key: str, request: Request, _: str = Depends(require_admin)):
    try:
        library.set_enabled(key, bool((await request.json()).get("enabled", True)))
    except KeyError:
        raise HTTPException(404, "Algoritmo sconosciuto")
    return library.listing()


@admin_routes.delete("/api/skills/{key:path}")
async def admin_skill_delete(key: str, user: str = Depends(require_admin)):
    try:
        library.delete(key)
    except KeyError:
        raise HTTPException(404, "Algoritmo sconosciuto")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    store.event("INFO", f"Algoritmo {key} eliminato da {user}", "skills")
    return library.listing()
