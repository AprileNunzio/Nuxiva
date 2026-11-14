from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from state import store

from agenti.nodes import trustpolicy
from agenti.nodes.audit import audit
from agenti.nodes.registry import registry

admin_routes = APIRouter()


class TrustBody(BaseModel):
    profile: str = Field(max_length=16)
    allow_second_server: bool = False
    grants: list[str] = Field(default_factory=list, max_length=8)


def _node(node_id: str) -> dict:
    node = registry.data["nodes"].get(node_id)
    if node is None:
        raise HTTPException(404, "node_not_found")
    return node


@admin_routes.get("/api/nodes/audit")
async def nodes_audit(limit: int = Query(100, ge=1, le=500), _: str = Depends(require_admin)):
    return {"entries": audit.tail(limit), "verify": audit.verify()}


@admin_routes.get("/api/nodes/{node_id}/trust")
async def nodes_trust(node_id: str, _: str = Depends(require_admin)):
    return trustpolicy.state(_node(node_id))


@admin_routes.put("/api/nodes/{node_id}/trust")
async def nodes_set_trust(node_id: str, body: TrustBody, user: str = Depends(require_admin)):
    node = _node(node_id)
    before = trustpolicy.state(node)
    try:
        result = registry.set_trust(node_id, body.profile, body.allow_second_server, body.grants)
    except ValueError as exc:
        audit.record(user, node_id, "profile.reject", str(exc))
        raise HTTPException(400, str(exc))
    audit.record(user, node_id, "profile.set",
                 f"{before['profile']}>{result['profile']} mode={result['mode']} second_server={result['second_server_allowed']} "
                 f"grants={','.join(result['grants'])}")
    store.event("INFO", f"Profilo del nodo {node_id} impostato da {user}: {result['profile']} ({result['mode']})", "nodes")
    return result
