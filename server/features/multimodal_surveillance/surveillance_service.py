import time
from typing import Dict, Any, List, Optional
from server.features.multimodal_surveillance.interfaces import (
    AudioChunkPayload,
    AudioEnhancedResult,
    VideoFramePayload,
    VisualEventLogEntry,
    SatelliteNodeConfig,
    SemanticSearchQuery,
    SemanticSearchResponse,
)
from server.features.multimodal_surveillance.audio_continuous_recorder import audio_continuous_recorder
from server.features.multimodal_surveillance.video_continuous_recorder import video_continuous_recorder
from server.features.multimodal_surveillance.node_device_registry import node_device_registry
from server.core.sensory_bus.event_router import sensory_bus
from server.core.event_sourcing.universal_space import UniversalObservation

class MultimodalSurveillanceService:
    def __init__(self):
        pass

    async def ingest_audio(self, payload: AudioChunkPayload) -> AudioEnhancedResult:
        result = audio_continuous_recorder.ingest_audio_chunk(payload)
        obs = UniversalObservation(
            modality="audio_continuous",
            source_id=f"{payload.node_id}:{payload.microphone_id}",
            raw_data=result.cleaned_audio_base64,
            metadata={
                "snr_gain": result.snr_improvement_db,
                "duration": result.duration_sec,
                "timestamp": result.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return result

    async def ingest_video_frame(self, payload: VideoFramePayload) -> VisualEventLogEntry:
        entry = video_continuous_recorder.ingest_frame(payload)
        obs = UniversalObservation(
            modality="video_continuous",
            source_id=f"{payload.node_id}:{payload.camera_id}",
            raw_data=entry.encrypted_frame_hash,
            metadata={
                "event_id": entry.event_id,
                "summary": entry.activity_summary,
                "entities_count": len(entry.entities),
                "timestamp": entry.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return entry

    def query_visual_memory(self, search: SemanticSearchQuery) -> SemanticSearchResponse:
        return video_continuous_recorder.query_semantic_logs(search)

    def auto_configure_node(
        self,
        node_id: str,
        name: str,
        endpoint_url: str,
        camera: Optional[str] = None,
        mic: Optional[str] = None,
        audio_out: Optional[str] = None,
        psk: Optional[str] = None
    ) -> SatelliteNodeConfig:
        return node_device_registry.auto_configure_satellite(
            node_id=node_id,
            name=name,
            endpoint_url=endpoint_url,
            detected_camera=camera,
            detected_mic=mic,
            detected_audio_out=audio_out,
            psk=psk
        )

    def list_nodes(self) -> List[SatelliteNodeConfig]:
        return node_device_registry.list_nodes()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return {
            "audio_metrics": audio_continuous_recorder.get_metrics(),
            "video_metrics": video_continuous_recorder.get_metrics(),
            "configured_nodes": len(node_device_registry.list_nodes()),
            "nodes": [n.model_dump() for n in node_device_registry.list_nodes()],
            "latest_visual_events": [e.model_dump() for e in video_continuous_recorder.get_latest_events(limit=10)]
        }

multimodal_surveillance_service = MultimodalSurveillanceService()
