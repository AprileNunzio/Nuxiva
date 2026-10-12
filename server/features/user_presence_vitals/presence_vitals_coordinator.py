import time
from typing import Dict, Any, Optional, List
from server.features.user_presence_vitals.interfaces import (
    UserHealthProfile,
    EmergencyContact,
    EmergencyEventLog,
)
from server.features.user_presence_vitals.emergency_detector import vitals_emergency_detector
from server.features.user_presence_vitals.emergency_broadcaster import home_emergency_broadcaster
from server.features.wearable_vitals_hub.interfaces import RealtimeVitalTelemetry, ConnectionStatus
from server.features.wearable_vitals_hub.device_registry import wearable_registry
from server.features.wearable_vitals_hub.vitals_service import wearable_vitals_service

class UserPresenceVitalsCoordinator:
    def __init__(self):
        self._profiles: Dict[str, UserHealthProfile] = {}
        self._user_realtime_vitals: Dict[str, RealtimeVitalTelemetry] = {}
        self._initialize_default_profile()

    def register_or_update_profile(self, profile: UserHealthProfile) -> UserHealthProfile:
        self._profiles[profile.user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> Optional[UserHealthProfile]:
        return self._profiles.get(user_id)

    def list_profiles(self) -> List[UserHealthProfile]:
        return list(self._profiles.values())

    async def on_user_approached_node(self, user_id: str, node_id: str) -> Dict[str, Any]:
        profile = self._profiles.get(user_id)
        if not profile:
            profile = self._create_adhoc_profile(user_id)

        connected_devices = []
        if profile.auto_connect_on_approach:
            for dev_id in profile.associated_wearable_ids:
                dev = wearable_registry.get_device(dev_id)
                if dev:
                    wearable_registry.update_status(dev_id, ConnectionStatus.CONNECTED)
                    connected_devices.append(dev.name)

        current_vitals = wearable_vitals_service.get_system_state().latest_vitals
        emergency_log = None
        broadcast_result = None

        if current_vitals:
            self._user_realtime_vitals[user_id] = current_vitals
            emergency_log = vitals_emergency_detector.evaluate_vitals(profile, current_vitals)
            if emergency_log:
                broadcast_result = await home_emergency_broadcaster.broadcast_emergency(
                    emergency_log,
                    profile.emergency_contacts
                )

        return {
            "status": "USER_RECOGNIZED_AND_MONITORED",
            "user_id": user_id,
            "node_id": node_id,
            "auto_connected_devices": connected_devices,
            "vitals": current_vitals.model_dump() if current_vitals else None,
            "emergency_triggered": emergency_log is not None,
            "emergency_details": emergency_log.model_dump() if emergency_log else None,
            "broadcast_status": broadcast_result
        }

    async def ingest_live_user_vitals(self, user_id: str, vitals: RealtimeVitalTelemetry) -> Dict[str, Any]:
        profile = self._profiles.get(user_id)
        if not profile:
            profile = self._create_adhoc_profile(user_id)

        self._user_realtime_vitals[user_id] = vitals
        await wearable_vitals_service.ingest_vital_telemetry(vitals)

        emergency = vitals_emergency_detector.evaluate_vitals(profile, vitals)
        broadcast_info = None
        if emergency:
            broadcast_info = await home_emergency_broadcaster.broadcast_emergency(
                emergency,
                profile.emergency_contacts
            )

        return {
            "user_id": user_id,
            "vitals": vitals.model_dump(),
            "emergency": emergency.model_dump() if emergency else None,
            "broadcast": broadcast_info
        }

    def _create_adhoc_profile(self, user_id: str) -> UserHealthProfile:
        p = UserHealthProfile(
            user_id=user_id,
            full_name=f"Utente {user_id}",
            associated_wearable_ids=["fitbit_edge_primary"],
            emergency_contacts=[
                EmergencyContact(
                    contact_id="cnt_primary_guardian",
                    name="Contatto Emergenza Principale",
                    relationship="Familiare",
                    phone_number="+39 340 1234567",
                    priority_order=1
                )
            ]
        )
        self._profiles[user_id] = p
        return p

    def _initialize_default_profile(self):
        owner_profile = UserHealthProfile(
            user_id="owner",
            full_name="Nunzio (Amministratore Primario)",
            associated_wearable_ids=["fitbit_edge_primary", "renpho_scale_01"],
            emergency_contacts=[
                EmergencyContact(
                    contact_id="cnt_family_01",
                    name="Contatto Famiglia Primario",
                    relationship="Familiare / Coniuge",
                    phone_number="+39 333 9876543",
                    notify_by_sms=True,
                    notify_by_call=True,
                    priority_order=1
                ),
                EmergencyContact(
                    contact_id="cnt_doctor_02",
                    name="Medico di Fiducia / Emergenze",
                    relationship="Medico",
                    phone_number="+39 347 1122334",
                    notify_by_sms=True,
                    notify_by_call=False,
                    priority_order=2
                )
            ]
        )
        self._profiles[owner_profile.user_id] = owner_profile

presence_vitals_coordinator = UserPresenceVitalsCoordinator()
