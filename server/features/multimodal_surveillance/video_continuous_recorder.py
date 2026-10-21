from collections import deque
from typing import Dict, Deque, List, Optional, Any
from server.features.multimodal_surveillance.interfaces import (
    VideoFramePayload,
    VisualEventLogEntry,
    SemanticSearchQuery,
    SemanticSearchResponse,
)
from server.features.multimodal_surveillance.frame_semantic_analyzer import frame_semantic_analyzer
from server.features.multimodal_surveillance.encryption_vault import vault

class ContinuousVideoRecorder:
    def __init__(self, max_event_history: int = 500):
        self._max_history = max_event_history
        self._camera_event_logs: Dict[str, Deque[VisualEventLogEntry]] = {}
        self._all_events_chronological: Deque[VisualEventLogEntry] = deque(maxlen=max_event_history)
        self._encrypted_log_vault: Dict[str, str] = {}
        self._total_frames_analyzed = 0

    def ingest_frame(self, frame: VideoFramePayload) -> VisualEventLogEntry:
        self._total_frames_analyzed += 1
        entry = frame_semantic_analyzer.analyze_frame(frame)

        cam_key = f"{frame.node_id}:{frame.camera_id}"
        if cam_key not in self._camera_event_logs:
            self._camera_event_logs[cam_key] = deque(maxlen=self._max_history)

        self._camera_event_logs[cam_key].append(entry)
        self._all_events_chronological.append(entry)

        enc_str = vault.encrypt_string(entry.model_dump_json())
        self._encrypted_log_vault[entry.event_id] = enc_str

        return entry

    def query_semantic_logs(self, query: SemanticSearchQuery) -> SemanticSearchResponse:
        tokens = [t.lower().strip() for t in query.query.split() if len(t.strip()) > 1]
        results: List[VisualEventLogEntry] = []

        is_courier_query = any(k in query.query.lower() for k in ["corriere", "consegna", "pacco", "dhl", "amazon", "poste"])

        for entry in reversed(self._all_events_chronological):
            if query.node_id and entry.node_id != query.node_id:
                continue
            if query.camera_id and entry.camera_id != query.camera_id:
                continue
            if query.time_from and entry.timestamp < query.time_from:
                continue
            if query.time_to and entry.timestamp > query.time_to:
                continue

            matches_query = False
            if is_courier_query and entry.courier_details:
                matches_query = True
            else:
                desc_lower = entry.detailed_description.lower()
                matched_token_count = sum(1 for tok in tokens if tok in desc_lower)
                if matched_token_count >= max(1, len(tokens) // 2):
                    matches_query = True

            if matches_query:
                results.append(entry)
                if len(results) >= query.limit:
                    break

        direct_answer = self._synthesize_direct_answer(query.query, results)
        return SemanticSearchResponse(
            query=query.query,
            total_found=len(results),
            direct_answer=direct_answer,
            matches=results
        )

    def get_latest_events(self, camera_key: Optional[str] = None, limit: int = 25) -> List[VisualEventLogEntry]:
        if camera_key and camera_key in self._camera_event_logs:
            return list(self._camera_event_logs[camera_key])[-limit:]
        return list(self._all_events_chronological)[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_frames_analyzed": self._total_frames_analyzed,
            "monitored_cameras": list(self._camera_event_logs.keys()),
            "stored_semantic_events": len(self._all_events_chronological),
            "encrypted_vault_entries": len(self._encrypted_log_vault)
        }

    def _synthesize_direct_answer(self, raw_query: str, matches: List[VisualEventLogEntry]) -> str:
        if not matches:
            return f"Nessun evento o dettaglio corrispondente trovato nei registri visivi per: '{raw_query}'."

        first = matches[0]
        if "corriere" in raw_query.lower() and first.courier_details:
            cd = first.courier_details
            person_desc = ""
            if first.person_details:
                person_desc = f" Indossava {first.person_details.get('clothing', '')} (colori {first.person_details.get('colors', '')})."
            veh_desc = ""
            if first.vehicle_details:
                veh_desc = f" Veicolo: {first.vehicle_details.get('type', '')} ({first.vehicle_details.get('color', '')})."
            return (
                f"Il corriere ({cd.get('provider', 'Sconosciuto')}) è arrivato alle ore {cd.get('time_arrival', 'N/D')} "
                f"rilevato dalla telecamera [{first.camera_id}].{person_desc}{veh_desc} Movimento: {cd.get('action', '')}."
            )

        return (
            f"Trovati {len(matches)} eventi rilevanti. Ultimo evento registrato alle {first.iso_timestamp} "
            f"sulla telecamera [{first.camera_id}]: {first.detailed_description}"
        )

video_continuous_recorder = ContinuousVideoRecorder()
