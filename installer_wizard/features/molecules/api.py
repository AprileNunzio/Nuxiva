from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from access import require_admin, require_display
from features.molecules.library import MAX_BYTES, EngineUnavailable, library
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
READ = {"x-nuxiva-capabilities": ["molecules.read"]}
MANAGE = {"x-nuxiva-capabilities": ["molecules.manage"]}


def _meta(mid: str) -> dict:
    try:
        return library.get(mid)
    except KeyError:
        raise HTTPException(404, "Molecola sconosciuta")


@public_routes.get("/api/molecules/{mid}/scene")
async def molecule_scene(mid: str, request: Request, lod: str = "atoms", scheme: str = "element"):
    require_display(request, "Solo dal display")
    _meta(mid)
    try:
        summary, packed = library.scene(mid, lod, scheme)
    except EngineUnavailable:
        raise HTTPException(503, "Motore molecolare non disponibile")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return Response(packed, media_type="application/octet-stream",
                    headers={"Cache-Control": "private, max-age=3600", "X-Molecule-Atoms": str(summary["atoms"]),
                             "X-Content-Type-Options": "nosniff"})


@admin_routes.get("/api/molecules", openapi_extra=READ)
async def molecules_list(_: str = Depends(require_admin)):
    import native_module
    from features.molecules.library import available
    return {"molecules": library.listing(), "engine": available(), "build": native_module.build_status()}


@admin_routes.post("/api/molecules/upload", openapi_extra=MANAGE)
async def molecules_upload(request: Request, name: str, title: str = "", user: str = Depends(require_admin)):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, "File troppo grande")
        chunks.append(chunk)
    data = b"".join(chunks)
    try:
        meta = library.add(name, data, title)
    except EngineUnavailable:
        raise HTTPException(503, "Motore molecolare non disponibile")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", f"Struttura molecolare caricata da {user}: {meta['title']}", "molecules")
    library.show(meta)
    return meta


@admin_routes.post("/api/molecules/{mid}/show", openapi_extra=READ)
async def molecules_show(mid: str, _: str = Depends(require_admin)):
    library.show(_meta(mid))
    return {"ok": True}


@admin_routes.delete("/api/molecules/{mid}", openapi_extra=MANAGE)
async def molecules_delete(mid: str, user: str = Depends(require_admin)):
    try:
        library.remove(mid)
    except KeyError:
        raise HTTPException(404, "Molecola sconosciuta")
    store.event("INFO", f"Struttura molecolare eliminata da {user}", "molecules")
    return {"ok": True}
