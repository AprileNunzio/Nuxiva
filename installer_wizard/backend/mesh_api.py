import asyncio
import ipaddress
import json
import logging
from typing import Literal

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

import auth
from access import require_admin
from mesh_topology import compose_topology, known_node_ids, paired_nodes, paired_source

log = logging.getLogger("nuxiva.mesh_api")

public_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])
admin_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])
_secured = APIRouter(dependencies=[Depends(require_admin)])


def _require_paired_node(request: Request) -> dict:
    from features.nodes.registry import registry

    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    try:
        return registry.authenticate(request.headers.get("x-nuxiva-node", ""), token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail="node_unauthorized") from exc


_peers = APIRouter(dependencies=[Depends(_require_paired_node)])

STREAM_INTERVAL_S = 0.5
WS_POLICY_VIOLATION = 1008

NODE_ID_PATTERN = r"^[A-Za-z0-9._:@-]{1,128}$"

try:
    from server.features.mesh_coordinator.p2p_mesh import VIRTUAL_CORE_ID, p2p_mesh
except ImportError:
    import sys
    from pathlib import Path
    server_dir = Path(__file__).resolve().parent.parent.parent / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    from features.mesh_coordinator.p2p_mesh import VIRTUAL_CORE_ID, p2p_mesh


@_secured.get("/topology")
async def get_mesh_topology(paired: list = Depends(paired_nodes)):
    return compose_topology(p2p_mesh, paired)


@_secured.get("/telemetry/{node_id}")
async def get_single_node_telemetry(node_id: str, paired: list = Depends(paired_nodes)):
    if node_id not in known_node_ids(p2p_mesh, paired):
        raise HTTPException(status_code=404, detail="node_not_found")
    return p2p_mesh.get_node_telemetry(node_id)


def _websocket_authorized(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin", "")
    host = websocket.headers.get("host", "")
    if not origin or not host or urlsplit(origin).netloc.lower() != host.lower():
        return False
    return auth.verify(websocket.cookies.get(auth.SESSION_COOKIE)) is not None


@admin_routes.websocket("/telemetry/stream")
async def websocket_telemetry_stream(websocket: WebSocket, provider=Depends(paired_source)):
    if not _websocket_authorized(websocket):
        await websocket.close(code=WS_POLICY_VIOLATION)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(compose_topology(p2p_mesh, provider()))
            await asyncio.sleep(STREAM_INTERVAL_S)
    except WebSocketDisconnect:
        log.debug("Client disconnesso dallo stream telemetrico")


class BindParentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    satellite_id: str = Field(pattern=NODE_ID_PATTERN, max_length=128)
    satellite_ip: str = Field(default="0.0.0.0", max_length=45)
    parent_node_id: str = Field(pattern=NODE_ID_PATTERN, max_length=128)
    parent_ip: str = Field(default="127.0.0.1", max_length=45)
    stream_type: Literal["audio_pcm", "rtsp_video", "sensor_telemetry"] = "audio_pcm"

    @field_validator("satellite_ip", "parent_ip")
    @classmethod
    def _valid_ip(cls, value: str) -> str:
        ipaddress.ip_address(value)
        return value


@_secured.post("/bind_parent")
async def bind_satellite_parent(req: BindParentRequest, paired: list = Depends(paired_nodes)):
    if req.satellite_id == req.parent_node_id:
        raise HTTPException(status_code=422, detail="self_binding_forbidden")
    if req.satellite_id == p2p_mesh.node_id:
        raise HTTPException(status_code=422, detail="host_binding_forbidden")
    known = known_node_ids(p2p_mesh, paired)
    if req.satellite_id not in known:
        raise HTTPException(status_code=404, detail="node_not_found")
    if req.parent_node_id not in known | {VIRTUAL_CORE_ID}:
        raise HTTPException(status_code=404, detail="parent_not_found")
    p2p_mesh.bind_satellite_to_parent(
        req.satellite_id, req.satellite_ip, req.parent_node_id, req.parent_ip, req.stream_type
    )
    return {"ok": True, "satellite_id": req.satellite_id, "parent_node_id": req.parent_node_id}


@_secured.get("/crdt")
@_peers.get("/crdt")
async def get_crdt_state():
    return JSONResponse(content=json.loads(p2p_mesh.export_crdt_state()))


@_secured.post("/crdt/merge")
@_peers.post("/crdt/merge")
async def merge_crdt_payload(request: Request):
    data = await request.json()
    count = p2p_mesh.merge_crdt_state(json.dumps(data))
    return {"ok": True, "updated_keys": count}


@_peers.post("/stream/direct_packet")
async def handle_direct_stream_packet(request: Request, node: dict = Depends(_require_paired_node)):
    sat_id = node["id"]
    body = await request.body()
    transferred = len(body)
    p2p_mesh.record_direct_stream_traffic(sat_id, transferred)
    return {"ok": True, "transferred_bytes": transferred, "direct": True}


admin_routes.include_router(_secured)
public_routes.include_router(_peers)
