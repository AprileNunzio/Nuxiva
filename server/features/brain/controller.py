import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from server.features.brain.contracts import (
    EngineVersionUpdateRequest,
    EngineVersionStatusResponse,
)
from server.features.brain.service import brain_engine_service

brain_router = APIRouter(prefix="/brain", tags=["brain"])

@brain_router.get("/engine-version", response_model=EngineVersionStatusResponse)
async def get_engine_version() -> EngineVersionStatusResponse:
    return brain_engine_service.get_status()

@brain_router.post("/engine-version", response_model=EngineVersionStatusResponse)
async def update_engine_version(payload: EngineVersionUpdateRequest) -> EngineVersionStatusResponse:
    return brain_engine_service.switch_engine(payload.version)

@brain_router.websocket("/engine-version/ws")
async def engine_version_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            telemetry = brain_engine_service.get_telemetry_snapshot()
            await websocket.send_json(telemetry.model_dump())
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
