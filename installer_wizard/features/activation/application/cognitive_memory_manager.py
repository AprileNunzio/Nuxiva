from __future__ import annotations

import logging

from features.activation.domain.memory_scheduler import ModelAllocation, ModelKind

log = logging.getLogger("nuxiva.activation.cognitive_memory_manager")


class CognitiveMemoryScheduler:
    def __init__(self, total_vram_mb: int, total_ram_mb: int) -> None:
        self._total_vram_mb = max(0, total_vram_mb)
        self._total_ram_mb = max(1024, total_ram_mb)
        self._active_models: dict[ModelKind, ModelAllocation] = {}

    @property
    def current_vram_usage(self) -> int:
        return sum(m.vram_mb for m in self._active_models.values() if m.loaded)

    @property
    def current_ram_usage(self) -> int:
        return sum(m.ram_mb for m in self._active_models.values() if m.loaded)

    def register_model(self, model: ModelAllocation) -> None:
        self._active_models[model.kind] = model

    def schedule_interaction(self, requested: ModelKind) -> list[ModelKind]:
        if requested not in self._active_models:
            return []

        target = self._active_models[requested]
        evicted: list[ModelKind] = []

        if self._total_vram_mb > 0:
            while not target.can_coexist_with(self._total_vram_mb, self.current_vram_usage):
                candidates = [
                    (k, m) for k, m in self._active_models.items()
                    if m.loaded and k != requested and m.priority < target.priority
                ]
                if not candidates:
                    break
                candidates.sort(key=lambda item: (item[1].priority.value, -item[1].vram_mb))
                victim_kind, victim_alloc = candidates[0]
                self._active_models[victim_kind] = ModelAllocation(
                    kind=victim_alloc.kind,
                    vram_mb=victim_alloc.vram_mb,
                    ram_mb=victim_alloc.ram_mb,
                    priority=victim_alloc.priority,
                    loaded=False,
                )
                evicted.append(victim_kind)

        self._active_models[requested] = ModelAllocation(
            kind=target.kind,
            vram_mb=target.vram_mb,
            ram_mb=target.ram_mb,
            priority=target.priority,
            loaded=True,
        )
        return evicted

    def to_dict(self) -> dict:
        return {
            "total_vram_mb": self._total_vram_mb,
            "total_ram_mb": self._total_ram_mb,
            "used_vram_mb": self.current_vram_usage,
            "used_ram_mb": self.current_ram_usage,
            "loaded_models": [k.value for k, m in self._active_models.items() if m.loaded],
        }
