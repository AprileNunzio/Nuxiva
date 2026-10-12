import uuid
import datetime
from typing import Dict, Any, List, Optional
from server.features.user_presence_vitals.interfaces import (
    EmergencySeverity,
    EmergencyVitalsThresholds,
    UserHealthProfile,
    EmergencyEventLog,
)
from server.features.wearable_vitals_hub.interfaces import RealtimeVitalTelemetry

class VitalsEmergencyDetector:
    def __init__(self):
        pass

    def evaluate_vitals(
        self,
        profile: UserHealthProfile,
        vitals: RealtimeVitalTelemetry
    ) -> Optional[EmergencyEventLog]:
        bpm = vitals.heart_rate_bpm
        spo2 = vitals.spo2_percentage
        temp = vitals.skin_temperature_celsius
        t = profile.thresholds

        severity = None
        reasons = []

        if bpm is not None:
            if bpm <= t.cardiac_arrest_min_bpm:
                severity = EmergencySeverity.FATAL_ARREST
                reasons.append(f"Arresto cardiaco o bradicardia estrema rilevata ({bpm} BPM)")
            elif bpm >= t.extreme_tachycardia_max_bpm:
                severity = EmergencySeverity.CRITICAL
                reasons.append(f"Tachicardia ventricolare critica rilevata ({bpm} BPM)")

        if spo2 is not None and spo2 <= t.hypoxia_critical_spo2:
            severity = severity or EmergencySeverity.CRITICAL
            reasons.append(f"Ipossia acuta / SpO2 critico al {spo2}%")

        if temp is not None:
            if temp <= t.hypothermia_min_temp:
                severity = severity or EmergencySeverity.WARNING
                reasons.append(f"Ipotermia grave rilevata ({temp}°C)")
            elif temp >= t.hyperthermia_max_temp:
                severity = severity or EmergencySeverity.WARNING
                reasons.append(f"Ipertermia severa rilevata ({temp}°C)")

        if not severity:
            return None

        event_id = f"emg_{profile.user_id}_{int(vitals.timestamp)}_{uuid.uuid4().hex[:6]}"
        iso_str = datetime.datetime.fromtimestamp(vitals.timestamp, tz=datetime.timezone.utc).isoformat()

        return EmergencyEventLog(
            event_id=event_id,
            user_id=profile.user_id,
            timestamp=vitals.timestamp,
            iso_timestamp=iso_str,
            severity=severity,
            trigger_reason=" | ".join(reasons),
            vitals_snapshot=vitals.model_dump(),
            contacts_notified=[c.name for c in profile.emergency_contacts],
            devices_broadcasted=["smart_speakers_all", "wall_monitors", "mesh_nodes"],
            resolved=False
        )

vitals_emergency_detector = VitalsEmergencyDetector()
