import uuid
from collections import deque
from typing import Dict, Deque, List, Any
from server.features.multimodal_surveillance.interfaces import (
    AudioChunkPayload,
    AudioEnhancedResult,
)
from server.features.multimodal_surveillance.audio_enhancer import audio_enhancer
from server.features.multimodal_surveillance.encryption_vault import vault

class ContinuousAudioRecorder:
    def __init__(self, max_buffer_segments: int = 120):
        self._max_buffer = max_buffer_segments
        self._node_buffers: Dict[str, Deque[AudioEnhancedResult]] = {}
        self._encrypted_vault_storage: Dict[str, str] = {}
        self._total_processed_chunks = 0

    def ingest_audio_chunk(self, chunk: AudioChunkPayload) -> AudioEnhancedResult:
        self._total_processed_chunks += 1
        enhanced = audio_enhancer.process_pcm16_base64(chunk.audio_base64)
        duration = float(enhanced.sample_count / float(chunk.sample_rate)) if chunk.sample_rate > 0 else 0.0

        segment_id = f"aud_{chunk.node_id}_{int(chunk.timestamp)}_{uuid.uuid4().hex[:6]}"
        result = AudioEnhancedResult(
            segment_id=segment_id,
            node_id=chunk.node_id,
            timestamp=chunk.timestamp,
            duration_sec=duration,
            original_rms=enhanced.original_rms,
            enhanced_rms=enhanced.enhanced_rms,
            snr_improvement_db=enhanced.snr_gain_db,
            cleaned_audio_base64=enhanced.cleaned_base64,
            acoustic_signature=enhanced.features,
            transcription_candidate=None
        )

        if chunk.node_id not in self._node_buffers:
            self._node_buffers[chunk.node_id] = deque(maxlen=self._max_buffer)
        self._node_buffers[chunk.node_id].append(result)

        encrypted_payload = vault.encrypt_string(result.model_dump_json())
        self._encrypted_vault_storage[segment_id] = encrypted_payload

        return result

    def get_latest_segments(self, node_id: str, limit: int = 20) -> List[AudioEnhancedResult]:
        buf = self._node_buffers.get(node_id)
        if not buf:
            return []
        items = list(buf)
        return items[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_processed_chunks": self._total_processed_chunks,
            "active_node_streams": list(self._node_buffers.keys()),
            "encrypted_vault_entries": len(self._encrypted_vault_storage)
        }


audio_continuous_recorder = ContinuousAudioRecorder()
