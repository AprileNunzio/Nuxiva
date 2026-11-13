from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from agenti.mcpclient import runtime, store

public_routes = APIRouter()
admin_routes = APIRouter()


@admin_routes.get("/api/mcp/servers")
async def listing(_: str = Depends(require_admin)):
    return {"servers": [store.public(i, r) for i, r in store.load().items()], "enabled": runtime.impl().enabled()}


@admin_routes.post("/api/mcp/servers")
async def add(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    try:
        server_id = runtime.add_server(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    count = await runtime.impl().sync_one(server_id)
    return {"id": server_id, "tools": count, "status": store.load()[server_id]["status"]}


@admin_routes.post("/api/mcp/servers/{server_id}/refresh")
async def refresh(server_id: str, _: str = Depends(require_admin)):
    if server_id not in store.load():
        raise HTTPException(404, "Server sconosciuto")
    count = await runtime.impl().sync_one(server_id)
    return {"tools": count, "status": store.load()[server_id]["status"]}


@admin_routes.put("/api/mcp/servers/{server_id}")
async def change(server_id: str, request: Request, _: str = Depends(require_admin)):
    if server_id not in store.load():
        raise HTTPException(404, "Server sconosciuto")
    body = await request.json()
    fields = {k: bool(body[k]) for k in ("enabled", "trusted", "lan") if k in body}
    store.update(server_id, **fields)
    await runtime.impl().sync_one(server_id)
    return {"ok": True}


@admin_routes.delete("/api/mcp/servers/{server_id}")
async def remove(server_id: str, _: str = Depends(require_admin)):
    if not store.remove(server_id):
        raise HTTPException(404, "Server sconosciuto")
    await runtime.forget(server_id)
    return {"ok": True}


@admin_routes.post("/api/mcp/tools/{tool_id}/approve")
async def approve(tool_id: str, _: str = Depends(require_admin)):
    if not runtime.rust():
        raise HTTPException(404, "Funzione non disponibile")
    try:
        await runtime.impl().approve(tool_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc.args[0]) if exc.args else "rifiutato")
    return {"ok": True}
