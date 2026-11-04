from fastapi import APIRouter
from server.features.wearable_vitals_hub.interfaces import (
    RealtimeVitalTelemetry,
    BodyCompositionData,
    WearableDeviceRegistration,
    WearableSystemState,
)
from server.features.wearable_vitals_hub.vitals_service import wearable_vitals_service

wearable_router = APIRouter(prefix="/wearables", tags=["wearable_vitals_hub"])

@wearable_router.get("/state", response_model=WearableSystemState)
async def get_wearables_overview() -> WearableSystemState:
    return wearable_vitals_service.get_system_state()

@wearable_router.post("/telemetry", response_model=RealtimeVitalTelemetry)
async def post_vital_telemetry(telemetry: RealtimeVitalTelemetry) -> RealtimeVitalTelemetry:
    return await wearable_vitals_service.ingest_vital_telemetry(telemetry)

@wearable_router.post("/body-composition", response_model=BodyCompositionData)
async def post_body_composition(data: BodyCompositionData) -> BodyCompositionData:
    return await wearable_vitals_service.ingest_body_composition(data)

@wearable_router.post("/devices", response_model=WearableDeviceRegistration)
async def register_wearable_device(device: WearableDeviceRegistration) -> WearableDeviceRegistration:
    return wearable_vitals_service.register_device(device)
