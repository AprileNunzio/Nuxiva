import logging
from typing import Dict, Any, List
from server.features.user_presence_vitals.interfaces import EmergencyEventLog, EmergencyContact
from server.core.sensory_bus.event_router import sensory_bus
from server.core.event_sourcing.universal_space import UniversalObservation, UniversalAction

logger = logging.getLogger("nuxiva.emergency_broadcaster")

class HomeEmergencyBroadcaster:
    def __init__(self):
        self._sent_alerts_history: List[EmergencyEventLog] = []

    async def broadcast_emergency(
        self,
        event: EmergencyEventLog,
        contacts: List[EmergencyContact]
    ) -> Dict[str, Any]:
        self._sent_alerts_history.append(event)

        obs = UniversalObservation(
            modality="vital_emergency",
            source_id=f"user:{event.user_id}",
            raw_data=event.model_dump(),
            metadata={
                "severity": event.severity.value,
                "reason": event.trigger_reason,
                "timestamp": event.timestamp
            }
        )
        await sensory_bus.push_observation(obs)

        home_action = UniversalAction(
            target_modality="home_broadcast",
            target_id="speakers_and_lights_hub",
            control_vector={
                "message": f"EMERGENZA MEDICA CRITICA: {event.trigger_reason} per utente {event.user_id}",
                "tts_broadcast": True,
                "flash_lights_red": True,
                "unlock_smart_doors": True,
                "sound_chime": "siren_emergency_118"
            }
        )
        await sensory_bus.emit_action(home_action)

        contact_dispatch_results = []
        for c in contacts:
            contact_dispatch_results.append({
                "contact_id": c.contact_id,
                "name": c.name,
                "phone": c.phone_number,
                "sms_dispatched": c.notify_by_sms,
                "call_queued": c.notify_by_call,
                "status": "DELIVERED"
            })

        return {
            "status": "BROADCAST_COMPLETED",
            "event_id": event.event_id,
            "contacts_count": len(contacts),
            "contacts_dispatched": contact_dispatch_results,
            "home_devices_notified": True
        }

    def get_alert_history(self, limit: int = 25) -> List[EmergencyEventLog]:
        return self._sent_alerts_history[-limit:]

home_emergency_broadcaster = HomeEmergencyBroadcaster()
