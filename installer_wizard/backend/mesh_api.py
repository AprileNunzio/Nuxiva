import asyncio
import json
import logging
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("nuxiva.mesh_api")

public_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])
admin_routes = APIRouter(prefix="/api/v5/mesh", tags=["mesh"])

try:
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
except ImportError:
    import sys
    from pathlib import Path
    server_dir = Path(__file__).resolve().parent.parent.parent / "server"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    from features.mesh_coordinator.p2p_mesh import p2p_mesh


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


@admin_routes.post("/bind_parent")
async def bind_satellite_parent(request: Request):
    """
    Associazione topologica (Parent Binding) via Drag & Drop o pulsante.
    """
    data = await request.json()
    sat_id = data.get("satellite_id")
    sat_ip = data.get("satellite_ip", "0.0.0.0")
    parent_id = data.get("parent_node_id")
    parent_ip = data.get("parent_ip", "127.0.0.1")
    stream_type = data.get("stream_type", "audio")

    if not sat_id or not parent_id:
        return JSONResponse({"ok": False, "error": "Parametri mancanti"}, status_code=400)

    p2p_mesh.bind_satellite_to_parent(sat_id, sat_ip, parent_id, parent_ip, stream_type)
    return {"ok": True, "satellite_id": sat_id, "parent_node_id": parent_id, "target_ip": parent_ip}


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
