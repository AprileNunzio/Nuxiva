from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time

class NodeRole(str, Enum):
    MASTER = "master"
    SATELLITE = "satellite"
    EDGE_SENSOR = "edge_sensor"

class SatelliteNodeConfig(BaseModel):
    node_id: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(..., min_length=2, max_length=128)
    role: NodeRole = NodeRole.SATELLITE
    endpoint_url: str = Field(..., pattern=r"^https?://[a-zA-Z0-9.\-_]+(:[0-9]+)?$")
    default_camera_id: str = Field(..., min_length=1, max_length=64)
    default_microphone_id: str = Field(..., min_length=1, max_length=64)
    default_audio_output_id: str = Field(..., min_length=1, max_length=64)
    psk_key: str = Field(..., min_length=16)
    is_active: bool = True
    last_heartbeat: float = Field(default_factory=time.time)

class AudioChunkPayload(BaseModel):
    node_id: str = Field(..., min_length=2, max_length=64)
    microphone_id: str = Field(..., min_length=1, max_length=64)
    timestamp: float = Field(default_factory=time.time)
    sample_rate: int = Field(16000, ge=8000, le=96000)
    audio_base64: str = Field(..., min_length=8)
    client_sequence: int = Field(0, ge=0)

class AudioEnhancedResult(BaseModel):
    segment_id: str
    node_id: str
    timestamp: float
    duration_sec: float
    original_rms: float
    enhanced_rms: float
    snr_improvement_db: float
    cleaned_audio_base64: str
    transcription_candidate: Optional[str] = None
    acoustic_signature: Dict[str, float] = Field(default_factory=dict)

class VisualEntityDetail(BaseModel):
    category: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    color_description: str
    clothing_details: Optional[str] = None
    movement_vector: Optional[str] = None
    face_attributes: Optional[Dict[str, Any]] = None
    bounding_box: List[float] = Field(default_factory=list)

class VideoFramePayload(BaseModel):
    node_id: str = Field(..., min_length=2, max_length=64)
    camera_id: str = Field(..., min_length=1, max_length=64)
    timestamp: float = Field(default_factory=time.time)
    frame_base64: str = Field(..., min_length=16)
    frame_sequence: int = Field(0, ge=0)

class VisualEventLogEntry(BaseModel):
    event_id: str
    node_id: str
    camera_id: str
    timestamp: float
    iso_timestamp: str
    detailed_description: str
    entities: List[VisualEntityDetail]
    courier_details: Optional[Dict[str, Any]] = None
    vehicle_details: Optional[Dict[str, Any]] = None
    person_details: Optional[Dict[str, Any]] = None
    activity_summary: str
    threat_level: str = "normal"
    encrypted_frame_hash: str

class SemanticSearchQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=512)
    node_id: Optional[str] = None
    camera_id: Optional[str] = None
    time_from: Optional[float] = None
    time_to: Optional[float] = None
    limit: int = Field(20, ge=1, le=100)

class SemanticSearchResponse(BaseModel):
    query: str
    total_found: int
    direct_answer: str
    matches: List[VisualEventLogEntry]
