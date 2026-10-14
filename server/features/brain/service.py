import time
from typing import List
from server.features.llm_gateway.contracts import CognitiveEngineVersion
from server.features.brain.contracts import (
    CognitiveEngineProfile,
    EngineVersionStatusResponse,
    EngineTelemetryUpdate,
)
from server.core.reasoning.engines.scanner import engine_scanner

class BrainEngineService:
    def __init__(self) -> None:
        self._scanner = engine_scanner
        default_engine = self._scanner.get_default_engine()
        self._configured_version: CognitiveEngineVersion = default_engine.version
        self._active_runtime_version: CognitiveEngineVersion = CognitiveEngineVersion.VELOCE_5_0
        self._last_switch_timestamp: float = time.time()

    def get_configured_version(self) -> CognitiveEngineVersion:
        return self._configured_version

    def get_active_runtime_version(self) -> CognitiveEngineVersion:
        return self._active_runtime_version

    def switch_engine(self, requested: CognitiveEngineVersion) -> EngineVersionStatusResponse:
        self._configured_version = requested
        if requested == CognitiveEngineVersion.AUTO_6_5:
            self._active_runtime_version = CognitiveEngineVersion.VELOCE_5_0
        else:
            self._active_runtime_version = requested
        self._last_switch_timestamp = time.time()
        return self.get_status()

    def update_runtime_escalation(self, new_runtime: CognitiveEngineVersion) -> None:
        if self._configured_version == CognitiveEngineVersion.AUTO_6_5:
            self._active_runtime_version = new_runtime

    def get_status(self) -> EngineVersionStatusResponse:
        active_engine = self._scanner.get_engine(self._active_runtime_version)
        if active_engine is None:
            active_engine = self._scanner.get_default_engine()
        profiles: List[CognitiveEngineProfile] = []
        for engine in self._scanner.list_engines():
            profiles.append(
                CognitiveEngineProfile(
                    id=engine.version,
                    name=engine.name,
                    architecture=engine.architecture,
                    latency_sla_ms=engine.latency_sla_ms,
                    vram_mb=engine.vram_mb,
                    active=(engine.version == self._configured_version),
                )
            )
        return EngineVersionStatusResponse(
            current_configured=self._configured_version,
            active_runtime=self._active_runtime_version,
            latency_sla_ms=active_engine.latency_sla_ms,
            vram_mb=active_engine.vram_mb,
            engines=profiles,
            success=True,
        )

    def get_telemetry_snapshot(self, psi: float = 0.20) -> EngineTelemetryUpdate:
        active_engine = self._scanner.get_engine(self._active_runtime_version)
        if active_engine is None:
            active_engine = self._scanner.get_default_engine()
        return EngineTelemetryUpdate(
            version=self._active_runtime_version,
            synaptic_latency_ms=float(active_engine.latency_sla_ms),
            vram_allocated_mb=int(active_engine.vram_mb),
            complexity_psi=round(psi, 4),
            neuromodulators={
                "dopamine": 0.82,
                "noradrenaline": 0.35,
                "serotonin": 0.65,
                "cortisol": 0.12,
            },
        )

brain_engine_service = BrainEngineService()
