import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

RAPL_ROOT = Path("/sys/class/powercap")
SUPPLY_ROOT = Path("/sys/class/power_supply")
MIN_SPAN_S = 0.5
MAX_WATTS = 5000.0


def _read_int(path: Path) -> Optional[int]:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def rapl_domains(root: Path = RAPL_ROOT) -> List[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("intel-rapl:*") if p.name.count(":") == 1 and (p / "energy_uj").is_file())


def battery_watts(root: Path = SUPPLY_ROOT) -> Optional[float]:
    if not root.is_dir():
        return None
    for supply in sorted(root.glob("BAT*")):
        power = _read_int(supply / "power_now")
        if power is not None and power > 0:
            return min(MAX_WATTS, power / 1e6)
        current, voltage = _read_int(supply / "current_now"), _read_int(supply / "voltage_now")
        if current and voltage and current > 0 and voltage > 0:
            return min(MAX_WATTS, current / 1e6 * voltage / 1e6)
    return None


class PowerProbe:
    def __init__(self, rapl_root: Path = RAPL_ROOT, supply_root: Path = SUPPLY_ROOT, clock=time.monotonic) -> None:
        self._rapl_root = rapl_root
        self._supply_root = supply_root
        self._clock = clock
        self._lock = threading.Lock()
        self._last: Optional[Tuple[float, dict]] = None

    def _sample(self) -> dict:
        return {d.name: _read_int(d / "energy_uj") for d in rapl_domains(self._rapl_root)}

    def cpu_watts(self) -> Optional[float]:
        now, sample = self._clock(), self._sample()
        with self._lock:
            previous, self._last = self._last, (now, sample)
        if previous is None:
            return None
        span = now - previous[0]
        if span < MIN_SPAN_S:
            return None
        total, seen = 0.0, False
        for name, energy in sample.items():
            before = previous[1].get(name)
            if energy is None or before is None or energy < before:
                continue
            total += (energy - before) / 1e6 / span
            seen = True
        return min(MAX_WATTS, total) if seen else None

    def system_watts(self, gpu_watts: Optional[float]) -> Optional[float]:
        cpu = self.cpu_watts()
        if cpu is not None:
            return round(cpu + (gpu_watts or 0.0), 1)
        battery = battery_watts(self._supply_root)
        if battery is not None:
            return round(battery, 1)
        return round(gpu_watts, 1) if gpu_watts is not None else None


power_probe = PowerProbe()
