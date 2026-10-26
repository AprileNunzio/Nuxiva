from __future__ import annotations

import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from access import require_admin
from node_commands import NodeCommandError, control_payload, describe, execute, unsupported_modules
from state import store
from tasks import background, delayed

admin_routes = APIRouter(prefix="/api/v5/nodes", tags=["Node Commands"], dependencies=[Depends(require_admin)])

_NODE_ID = re.compile(r"^[A-Za-z0-9._:@-]{1,128}$")
_COMMAND = re.compile(r"^[a-z]{2,16}$")


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False


def _mesh():
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh

    return p2p_mesh


def _validated(node_id: str) -> str:
    if not _NODE_ID.match(node_id):
        raise HTTPException(status_code=422, detail="invalid_node_id")
    return node_id


def _schedule_local(command: tuple) -> None:
    background(delayed(*command))


def _reopen_setup(user: str) -> None:
    import setup_api

    setup_api.reopen(user)


@admin_routes.get("/{node_id}/control")
async def node_control(node_id: str) -> Dict[str, Any]:
    mesh = _mesh()
    control = describe(_validated(node_id), mesh.node_id)
    return control_payload(control, True if control.scope == "local" else None, unsupported_modules(control))


@admin_routes.post("/{node_id}/commands/{command}")
async def node_command(node_id: str, command: str, req: CommandRequest, user: str = Depends(require_admin)) -> Dict[str, Any]:
    if not _COMMAND.match(command):
        raise HTTPException(status_code=422, detail="invalid_command")
    control = describe(_validated(node_id), _mesh().node_id)
    try:
        result = execute(control, command, req.confirm, _schedule_local, reopen_setup=lambda: _reopen_setup(user))
    except NodeCommandError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc
    store.event("WARN" if command == "reboot" else "INFO", f"Comando {command} al nodo {node_id} da {user}", "nodes", node_id=node_id)
    return result
