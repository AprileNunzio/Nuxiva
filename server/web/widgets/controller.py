import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from server.web.widgets.scanner import widget_scanner
from server.core.scanner.watcher import registry_watcher

widget_router = APIRouter(prefix="/widgets", tags=["Dynamic Widgets"])

class WidgetActionPayload(BaseModel):
    action: str
    payload: Dict[str, Any] = {}

class WidgetResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    icon: str
    render_type: str
    grid_span: Dict[str, int]
    state: Dict[str, Any] = {}

@widget_router.get("", response_model=List[WidgetResponse])
async def list_widgets() -> List[WidgetResponse]:
    widgets = widget_scanner.scan_all()
    results = []
    for w in widgets.values():
        state = await w.get_state()
        results.append(
            WidgetResponse(
                id=w.widget_id,
                name=w.manifest.name,
                category=w.manifest.category,
                description=w.manifest.description,
                icon=w.manifest.icon,
                render_type=w.render_type,
                grid_span=w.manifest.metadata.get("grid_span", {"col": 1, "row": 1}),
                state=state,
            )
        )
    return results

@widget_router.get("/{widget_id}/state")
async def get_widget_state(widget_id: str) -> Dict[str, Any]:
    widget = widget_scanner.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")
    state = await widget.get_state()
    return {"id": widget.widget_id, "state": state}

@widget_router.post("/{widget_id}/action")
async def execute_widget_action(widget_id: str, body: WidgetActionPayload) -> Dict[str, Any]:
    widget = widget_scanner.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found")
    result = await widget.execute_action(body.action, body.payload)
    return {"id": widget.widget_id, "action": body.action, "result": result}

@widget_router.websocket("/ws")
async def widget_stream_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = asyncio.Queue()

    async def on_registry_event(domain: str, event_type: str, data: Dict[str, Any]) -> None:
        if domain == "widgets":
            await queue.put({"type": "WIDGET_REGISTRY_EVENT", "event": event_type, "data": data})

    registry_watcher.subscribe(on_registry_event)
    try:
        initial_widgets = widget_scanner.scan_all()
        snapshot = []
        for w in initial_widgets.values():
            st = await w.get_state()
            snapshot.append({
                "id": w.widget_id,
                "name": w.manifest.name,
                "category": w.manifest.category,
                "description": w.manifest.description,
                "icon": w.manifest.icon,
                "render_type": w.render_type,
                "grid_span": w.manifest.metadata.get("grid_span", {"col": 1, "row": 1}),
                "state": st,
            })
        await websocket.send_json({"type": "WIDGETS_SNAPSHOT", "widgets": snapshot})

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "HEARTBEAT"})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
