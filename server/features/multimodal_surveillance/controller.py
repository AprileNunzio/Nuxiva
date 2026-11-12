from fastapi import APIRouter
from typing import Dict, Any, List
from server.features.multimodal_surveillance.interfaces import (
    AudioChunkPayload,
    AudioEnhancedResult,
    VideoFramePayload,
    VisualEventLogEntry,
    SatelliteNodeConfig,
    SemanticSearchQuery,
    SemanticSearchResponse,
)
from server.features.multimodal_surveillance.surveillance_service import multimodal_surveillance_service

surveillance_router = APIRouter(prefix="/surveillance", tags=["multimodal_surveillance"])

@surveillance_router.post("/audio/stream", response_model=AudioEnhancedResult)
async def ingest_audio_stream(payload: AudioChunkPayload) -> AudioEnhancedResult:
    return await multimodal_surveillance_service.ingest_audio(payload)

@surveillance_router.post("/video/frame", response_model=VisualEventLogEntry)
async def ingest_video_frame(payload: VideoFramePayload) -> VisualEventLogEntry:
    return await multimodal_surveillance_service.ingest_video_frame(payload)

@surveillance_router.post("/query", response_model=SemanticSearchResponse)
async def query_surveillance_memory(search: SemanticSearchQuery) -> SemanticSearchResponse:
    return multimodal_surveillance_service.query_visual_memory(search)

@surveillance_router.get("/nodes", response_model=List[SatelliteNodeConfig])
async def list_surveillance_nodes() -> List[SatelliteNodeConfig]:
    return multimodal_surveillance_service.list_nodes()

@surveillance_router.post("/nodes/autoconfig", response_model=SatelliteNodeConfig)
async def autoconfigure_satellite_node(config: SatelliteNodeConfig) -> SatelliteNodeConfig:
    return multimodal_surveillance_service.auto_configure_node(
        node_id=config.node_id,
        name=config.name,
        endpoint_url=config.endpoint_url,
        camera=config.default_camera_id,
        mic=config.default_microphone_id,
        audio_out=config.default_audio_output_id,
        psk=config.psk_key
    )

@surveillance_router.get("/dashboard")
async def get_surveillance_dashboard() -> Dict[str, Any]:
    return multimodal_surveillance_service.get_dashboard_summary()
