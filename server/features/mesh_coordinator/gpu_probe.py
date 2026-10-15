import logging
import re
import shutil
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

log = logging.getLogger("nuxiva.mesh.gpu")

CACHE_SECONDS = 5.0
NVIDIA_FIELDS = "name,memory.used,memory.total,power.draw,utilization.gpu,temperature.gpu"
DRM = Path("/sys/class/drm")
VENDORS = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x8086": "Intel"}
CARD_RE = re.compile(r"^card\d+$")


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vendor: str
    vram_used_gb: Optional[float] = None
    vram_total_gb: Optional[float] = None
    power_watts: Optional[float] = None
    utilization: Optional[float] = None
    temp_c: Optional[float] = None

    def as_dict(self) -> dict:
        return asdict(self)


def _number(text: str) -> Optional[float]:
    try:
        return float(text.strip())
    except ValueError:
        return None


def _gb(mib: Optional[float]) -> Optional[float]:
    return round(mib / 1024, 2) if mib is not None else None


def parse_nvidia(output: str) -> List[GpuInfo]:
    gpus = []
    for line in output.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6 or not parts[0]:
            continue
        gpus.append(GpuInfo(name=parts[0][:96], vendor="NVIDIA", vram_used_gb=_gb(_number(parts[1])),
                            vram_total_gb=_gb(_number(parts[2])), power_watts=_number(parts[3]),
                            utilization=_number(parts[4]), temp_c=_number(parts[5])))
    return gpus


def _nvidia() -> List[GpuInfo]:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return []
    try:
        proc = subprocess.run([binary, f"--query-gpu={NVIDIA_FIELDS}", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("nvidia-smi non risponde: %s", exc)
        return []
    if proc.returncode != 0:
        log.info("nvidia-smi ha restituito %s: %s", proc.returncode, proc.stderr.strip()[:200])
        return []
    return parse_nvidia(proc.stdout)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _pci_name(slot: str) -> str:
    binary = shutil.which("lspci")
    if not binary or not slot:
        return ""
    try:
        proc = subprocess.run([binary, "-mm", "-s", slot], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.info("lspci non disponibile: %s", exc)
        return ""
    fields = re.findall(r'"([^"]*)"', proc.stdout)
    return " ".join(f for f in fields[1:3] if f)[:96] if len(fields) >= 3 else ""


def drm_gpus(root: Path = DRM, namer: Callable[[str], str] = _pci_name, skip_nvidia: bool = False) -> List[GpuInfo]:
    gpus, seen = [], set()
    if not root.is_dir():
        return gpus
    for card in sorted(p for p in root.iterdir() if CARD_RE.match(p.name)):
        device = card / "device"
        vendor = VENDORS.get(_read(device / "vendor").lower())
        if not vendor or (skip_nvidia and vendor == "NVIDIA"):
            continue
        slot = next((line.split("=", 1)[1] for line in _read(device / "uevent").splitlines()
                     if line.startswith("PCI_SLOT_NAME=")), "")
        if slot in seen:
            continue
        seen.add(slot)
        total = _number(_read(device / "mem_info_vram_total") or "x")
        used = _number(_read(device / "mem_info_vram_used") or "x")
        busy = _number(_read(device / "gpu_busy_percent") or "x")
        gpus.append(GpuInfo(name=namer(slot) or f"{vendor} GPU", vendor=vendor,
                            vram_used_gb=round(used / 2**30, 2) if used is not None else None,
                            vram_total_gb=round(total / 2**30, 2) if total is not None else None,
                            utilization=busy))
    return gpus


class GpuProbe:
    def __init__(self, ttl: float = CACHE_SECONDS) -> None:
        self.ttl = ttl
        self._lock = threading.Lock()
        self._at = 0.0
        self._gpus: List[GpuInfo] = []

    def gpus(self) -> List[GpuInfo]:
        with self._lock:
            if time.monotonic() - self._at >= self.ttl:
                nvidia = _nvidia()
                self._gpus = nvidia + drm_gpus(skip_nvidia=bool(nvidia))
                self._at = time.monotonic()
            return list(self._gpus)

    def summary(self) -> dict:
        gpus = self.gpus()
        used = [g.vram_used_gb for g in gpus if g.vram_used_gb is not None]
        total = [g.vram_total_gb for g in gpus if g.vram_total_gb is not None]
        power = [g.power_watts for g in gpus if g.power_watts is not None]
        return {
            "gpu_name": gpus[0].name if gpus else None,
            "gpu_count": len(gpus),
            "gpus": [g.as_dict() for g in gpus],
            "vram_used_gb": round(sum(used), 2) if used else None,
            "vram_total_gb": round(sum(total), 2) if total else None,
            "gpu_power_watts": round(sum(power), 1) if power else None,
        }


gpu_probe = GpuProbe()
