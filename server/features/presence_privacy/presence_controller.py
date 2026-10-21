from typing import List
from fastapi import APIRouter
from server.features.presence_privacy.models import (
    PresenceStatus,
    VerificationPayload,
    SystemTelemetryData,
    WidgetPrivacyPolicy,
)
from server.features.presence_privacy.presence_service import presence_service
from server.features.presence_privacy.system_metrics import system_metrics_collector
from server.features.presence_privacy.vision_telemetry import (
    VisionTelemetryPayload,
    VisionTelemetryConfig,
    vision_telemetry_manager,
)

presence_router = APIRouter(prefix="/presence", tags=["presence"])
system_router = APIRouter(prefix="/system", tags=["system"])
privacy_router = APIRouter(prefix="/privacy", tags=["privacy"])

@presence_router.get("/status", response_model=PresenceStatus)
async def get_presence_status() -> PresenceStatus:
    return presence_service.get_status()

@presence_router.post("/verify", response_model=PresenceStatus)
async def record_presence_verification(payload: VerificationPayload) -> PresenceStatus:
    return presence_service.record_verification(payload)

@presence_router.post("/toggle-mock", response_model=PresenceStatus)
async def toggle_mock_presence(approaching: bool = True, verified: bool = True) -> PresenceStatus:
    res = presence_service.set_presence(approaching=approaching, verified=verified, user="owner")
    if approaching and verified:
        from server.features.user_presence_vitals.presence_vitals_coordinator import presence_vitals_coordinator
        import asyncio
        asyncio.create_task(presence_vitals_coordinator.on_user_approached_node("owner", "master_server"))
    return res

@system_router.get("/metrics", response_model=SystemTelemetryData)
async def get_system_metrics() -> SystemTelemetryData:
    return system_metrics_collector.collect()

@presence_router.get("/hud/projects")
async def get_proximity_hud_projects():
    status = presence_service.get_status()
    if not (status.is_owner_approaching or status.is_biometrically_verified):
        return {
            "unlocked": False,
            "reason": "Nessun utente autorizzato in prossimità del monitor",
            "detected_user": None,
            "projects": [],
        }

    from server.features.project_workspace.manager import project_manager
    from server.features.chatbot_mesh.user_agent_customization_service import user_agent_customization_service
    from server.core.security_guard.rbac_service import rbac_service

    detected = status.detected_user or "user_primary"
    user_account = rbac_service.get_user(detected)
    user_display = user_account.display_name if user_account else "Utente Primario"

    # Personalizzazioni per l'utente rilevato
    personalizations = user_agent_customization_service.list_user_personalizations(detected)

    active_projects = [
        {
            "project_id": p.project_id,
            "name": p.name,
            "goal": p.goal,
            "completion_percentage": p.completion_percentage,
            "autonomous_247": p.autonomous_247,
            "assigned_agents": p.assigned_agents,
            "milestones_count": len(p.milestones),
            "status": p.status,
        }
        for p in project_manager.get_all(detected)
        if p.status == "ACTIVE"
    ]

    return {
        "unlocked": True,
        "detected_user": detected,
        "display_name": user_display,
        "role": user_account.role.value if user_account else "owner_admin",
        "verification_method": status.verification_method,
        "confidence": status.confidence_score,
        "projects_count": len(active_projects),
        "projects": active_projects,
        "active_personalizations_count": len(personalizations),
    }

@privacy_router.get("/policies", response_model=List[WidgetPrivacyPolicy])
async def get_privacy_policies() -> List[WidgetPrivacyPolicy]:
    return presence_service.get_policies()

@presence_router.post("/vision/telemetry")
async def record_vision_telemetry(payload: VisionTelemetryPayload):
    return await vision_telemetry_manager.process_telemetry(payload)

@presence_router.get("/vision/state")
async def get_vision_state():
    return vision_telemetry_manager.get_latest_state()

@presence_router.post("/vision/config")
async def update_vision_config(config: VisionTelemetryConfig):
    return vision_telemetry_manager.update_config(config)

