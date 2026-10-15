import asyncio
import ipaddress
import json
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

log = logging.getLogger("nuxiva.mesh_api")

public_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])
admin_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])

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


@admin_routes.get("/topology")
@public_routes.get("/topology")
async def get_mesh_topology():
    """Restituisce il grafo topologico completo per il canvas :8080."""
    return p2p_mesh.get_mesh_canvas_state()


@admin_routes.get("/telemetry/{node_id}")
@public_routes.get("/telemetry/{node_id}")
async def get_single_node_telemetry(node_id: str):
    """Restituisce la telemetria real-time del nodo richiesto per l'hover HUD."""
    return p2p_mesh.get_node_telemetry(node_id)


@admin_routes.websocket("/telemetry/stream")
@public_routes.websocket("/telemetry/stream")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    WebSocket ad alta frequenza (2Hz) per l'HUD telemetrico real-time in hover.
    Invia snapshot telemetrici di tutti i nodi connessi.
    """
    await websocket.accept()
    try:
        while True:
            state = p2p_mesh.get_mesh_canvas_state()
            await websocket.send_json(state)
            await asyncio.sleep(0.5)  # 2 Hz
    except WebSocketDisconnect:
        log.debug("Client disconnesso dallo stream telemetrico")
    except Exception as exc:
        log.debug(f"Errore stream telemetrico: {exc}")


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


@admin_routes.post("/bind_parent")
async def bind_satellite_parent(req: BindParentRequest):
    if req.satellite_id == req.parent_node_id:
        raise HTTPException(status_code=422, detail="self_binding_forbidden")
    if req.satellite_id == p2p_mesh.node_id:
        raise HTTPException(status_code=422, detail="host_binding_forbidden")
    if req.satellite_id not in p2p_mesh.peers:
        raise HTTPException(status_code=404, detail="node_not_found")
    known_parents = {p2p_mesh.node_id, VIRTUAL_CORE_ID, *p2p_mesh.peers.keys()}
    if req.parent_node_id not in known_parents:
        raise HTTPException(status_code=404, detail="parent_not_found")
    p2p_mesh.bind_satellite_to_parent(
        req.satellite_id, req.satellite_ip, req.parent_node_id, req.parent_ip, req.stream_type
    )
    return {"ok": True, "satellite_id": req.satellite_id, "parent_node_id": req.parent_node_id}


@admin_routes.get("/crdt")
@public_routes.get("/crdt")
async def get_crdt_state():
    """Restituisce lo stato CRDT serializzato del Control Plane Condiviso."""
    return JSONResponse(content=json.loads(p2p_mesh.export_crdt_state()))


@admin_routes.post("/crdt/merge")
@public_routes.post("/crdt/merge")
async def merge_crdt_payload(request: Request):
    """Fonde uno stato CRDT remoto ricevuto da un altro PC della Mesh."""
    data = await request.json()
    count = p2p_mesh.merge_crdt_state(json.dumps(data))
    return {"ok": True, "updated_keys": count}


@public_routes.post("/stream/direct_packet")
async def handle_direct_stream_packet(request: Request):
    """
    Riceve un chunk di streaming diretto da un satellite.
    Verifica l'offload diretto al 100% sul nodo padre.
    """
    sat_id = request.headers.get("x-nuxiva-satellite-id", "")
    body = await request.body()
    transferred = len(body)
    p2p_mesh.record_direct_stream_traffic(sat_id, transferred)
    return {"ok": True, "transferred_bytes": transferred, "direct": True}
