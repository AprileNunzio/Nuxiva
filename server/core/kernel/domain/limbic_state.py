import math
import time
from dataclasses import dataclass


@dataclass
class LimbicState:
    dopamine: float = 0.5
    noradrenaline: float = 0.2
    serotonin: float = 0.6
    cortisol: float = 0.1
    last_update_ts: float = 0.0

    def __post_init__(self) -> None:
        if self.last_update_ts <= 0.0:
            self.last_update_ts = time.time()
        self._clamp_all()

    def _clamp_all(self) -> None:
        self.dopamine = max(0.0, min(1.0, float(self.dopamine)))
        self.noradrenaline = max(0.0, min(1.0, float(self.noradrenaline)))
        self.serotonin = max(0.0, min(1.0, float(self.serotonin)))
        self.cortisol = max(0.0, min(1.0, float(self.cortisol)))

    def apply_homeostatic_decay(self, current_ts: float | None = None, half_life_s: float = 30.0) -> None:
        ts = time.time() if current_ts is None else current_ts
        dt = max(0.0, ts - self.last_update_ts)
        self.last_update_ts = ts
        if dt <= 0.0:
            return
        decay_factor = math.exp(-dt / max(half_life_s, 1.0))
        target_d = 0.4
        target_na = 0.15
        target_5ht = 0.6
        target_c = 0.1
        self.dopamine = target_d + (self.dopamine - target_d) * decay_factor
        self.noradrenaline = target_na + (self.noradrenaline - target_na) * decay_factor
        self.serotonin = target_5ht + (self.serotonin - target_5ht) * decay_factor
        self.cortisol = target_c + (self.cortisol - target_c) * decay_factor
        self._clamp_all()

    def excite_emergency(self, magnitude: float = 0.5) -> None:
        self.noradrenaline = min(1.0, self.noradrenaline + magnitude * 0.4)
        self.cortisol = min(1.0, self.cortisol + magnitude * 0.2)
        self.serotonin = max(0.0, self.serotonin - magnitude * 0.2)
        self._clamp_all()

    def excite_reward(self, magnitude: float = 0.4) -> None:
        self.dopamine = min(1.0, self.dopamine + magnitude * 0.5)
        self.serotonin = min(1.0, self.serotonin + magnitude * 0.2)
        self.cortisol = max(0.0, self.cortisol - magnitude * 0.3)
        self._clamp_all()

    def excite_empathy(self, magnitude: float = 0.3) -> None:
        self.serotonin = min(1.0, self.serotonin + magnitude * 0.4)
        self.noradrenaline = max(0.0, self.noradrenaline - magnitude * 0.2)
        self._clamp_all()

    def excite_stress(self, magnitude: float = 0.4) -> None:
        self.cortisol = min(1.0, self.cortisol + magnitude * 0.5)
        self.noradrenaline = min(1.0, self.noradrenaline + magnitude * 0.3)
        self.dopamine = max(0.0, self.dopamine - magnitude * 0.3)
        self._clamp_all()

    def modulate_firing_threshold(self, base_vth: float = 0.85) -> float:
        return max(0.2, base_vth * (1.0 - 0.4 * self.noradrenaline))

    def modulate_parallel_lanes(self, base_lanes: int = 4) -> int:
        lanes = int(round(base_lanes + 4.0 * self.dopamine))
        return max(2, min(8, lanes))

    def modulate_stdp_rate(self, base_eta: float = 0.01) -> float:
        return base_eta * (1.0 + self.dopamine)

    def coalescence_window_s(self) -> float:
        return (35.0 + 85.0 * self.serotonin) / 1000.0

    def modulate_temperature(self, base_temp: float = 0.7) -> float:
        return max(0.1, base_temp * (1.0 - 0.6 * self.cortisol))

    def requires_critical_consensus(self) -> bool:
        return self.cortisol >= 0.45

    def modulate_ignition(self, base_threshold: float = 0.85) -> float:
        factor = (1.0 - 0.25 * self.noradrenaline + 0.15 * self.cortisol)
        return max(0.3, min(1.2, base_threshold * factor))

    def to_vector(self) -> list[float]:
        return [self.dopamine, self.noradrenaline, self.serotonin, self.cortisol]

    def to_dict(self) -> dict:
        return {
            "dopamine": round(self.dopamine, 4),
            "noradrenaline": round(self.noradrenaline, 4),
            "serotonin": round(self.serotonin, 4),
            "cortisol": round(self.cortisol, 4),
            "last_update_ts": self.last_update_ts,
        }
