from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from access import require_admin
from state import store

from features.nodes.compute import ollama_ready
from features.nodes.relay import RelayError, relay
from features.nodes.registry import registry

public_routes = APIRouter()
admin_routes = APIRouter()
POLL_SECONDS = 25.0
CHUNK_LIMIT = 400_000


def _node(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    try:
        return registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError:
        raise HTTPException(401, "node_unauthorized")


@public_routes.post("/api/nodes/compute/next")
async def compute_next(request: Request):
    node = _node(request)
    return {"jobs": await relay.take(node["id"], POLL_SECONDS)}


@public_routes.post("/api/nodes/compute/chunk")
async def compute_chunk(request: Request):
    node = _node(request)
    if int(request.headers.get("content-length") or 0) > CHUNK_LIMIT:
        raise HTTPException(413, "payload_too_large")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_request")
    try:
        cancel = relay.push(node["id"], body)
    except RelayError as exc:
        raise HTTPException(exc.status, exc.code)
    return {"cancel": cancel}


@admin_routes.api_route("/api/nodes/{node_id}/ollama/{path:path}", methods=["GET", "POST"])
async def node_ollama(node_id: str, path: str, request: Request, user: str = Depends(require_admin)):
    node = registry.data["nodes"].get(node_id)
    if node is None:
        raise HTTPException(404, "node_not_found")
    if not ollama_ready(node):
        raise HTTPException(409, "compute_ollama_not_shared")
    body = await request.body()
    try:
        job = relay.submit(node_id, request.method, "/" + path, body)
        status, content_type, stream = await relay.open(job)
    except RelayError as exc:
        raise HTTPException(exc.status, exc.code)
    store.event("INFO", f"Ollama del nodo {node_id}: {request.method} /{path} da {user}", "nodes")
    return StreamingResponse(stream, status_code=status, media_type=content_type)
