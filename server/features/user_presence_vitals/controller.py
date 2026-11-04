from fastapi import APIRouter
from typing import Dict, Any, List
from server.features.user_presence_vitals.interfaces import (
    UserHealthProfile,
    EmergencyEventLog,
)
from server.features.user_presence_vitals.presence_vitals_coordinator import presence_vitals_coordinator
from server.features.user_presence_vitals.emergency_broadcaster import home_emergency_broadcaster
from server.features.wearable_vitals_hub.interfaces import RealtimeVitalTelemetry

emergency_presence_router = APIRouter(prefix="/emergency-vitals", tags=["user_presence_vitals"])

@emergency_presence_router.get("/profiles", response_model=List[UserHealthProfile])
async def list_user_health_profiles() -> List[UserHealthProfile]:
    return presence_vitals_coordinator.list_profiles()

@emergency_presence_router.post("/profiles", response_model=UserHealthProfile)
async def update_health_profile(profile: UserHealthProfile) -> UserHealthProfile:
    return presence_vitals_coordinator.register_or_update_profile(profile)

@emergency_presence_router.post("/approach-event")
async def trigger_user_approach(user_id: str, node_id: str = "master_server") -> Dict[str, Any]:
    return await presence_vitals_coordinator.on_user_approached_node(user_id, node_id)

@emergency_presence_router.post("/ingest-user-vitals")
async def ingest_user_vitals_and_check(user_id: str, vitals: RealtimeVitalTelemetry) -> Dict[str, Any]:
    return await presence_vitals_coordinator.ingest_live_user_vitals(user_id, vitals)

@emergency_presence_router.get("/alert-history", response_model=List[EmergencyEventLog])
async def get_emergency_alert_history() -> List[EmergencyEventLog]:
    return home_emergency_broadcaster.get_alert_history()
