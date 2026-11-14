import ctypes
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

GIB = 1 << 30
NO_WINDOW = 0x08000000


class Mode(str, Enum):
    SERVER = "server"
    AUTO = "auto"
    LOCAL = "local"


@dataclass(frozen=True)
class Hardware:
    cores: int
    ram_gb: float
    gpu_name: str
    vram_gb: float


@dataclass(frozen=True)
class Tier:
    name: str
    stt_model: str
    brain_models: tuple[str, ...]
    gpu: bool


TIERS = (
    Tier("workstation", "large-v3", ("qwen3:32b", "llama3.3:70b", "qwen3:14b"), True),
    Tier("performance", "medium", ("qwen3:14b", "qwen3:8b"), True),
    Tier("standard", "small", ("qwen3:8b", "qwen3:4b"), False),
    Tier("light", "base", ("qwen3:4b", "qwen3:1.7b"), False),
    Tier("minimal", "tiny", ("qwen3:1.7b", "qwen3:0.6b"), False),
)


def parse_mode(value) -> Mode:
    try:
        return Mode(str(value).strip().lower())
    except ValueError:
        return Mode.AUTO


class _Memory(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                ("avail", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong), ("page_avail", ctypes.c_ulonglong),
                ("virtual_total", ctypes.c_ulonglong), ("virtual_avail", ctypes.c_ulonglong),
                ("extended", ctypes.c_ulonglong)]


def _ram_gb() -> float:
    status = _Memory()
    status.length = ctypes.sizeof(_Memory)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return round(status.total / GIB, 1)
    return 0.0


def _gpu() -> tuple[str, float]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return "", 0.0
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True,
                             text=True, timeout=5, creationflags=NO_WINDOW, check=False).stdout
        name, memory = [part.strip() for part in out.strip().splitlines()[0].split(",")][:2]
        return name, round(float(memory) / 1024, 1)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return "", 0.0


def detect() -> Hardware:
    name, vram = _gpu()
    return Hardware(os.cpu_count() or 1, _ram_gb(), name, vram)


def recommend(hardware: Hardware) -> Tier:
    gpu = hardware.vram_gb
    if gpu >= 20 and hardware.ram_gb >= 32:
        return TIERS[0]
    if gpu >= 10 and hardware.ram_gb >= 16:
        return TIERS[1]
    if hardware.ram_gb >= 16 and hardware.cores >= 8:
        return TIERS[2]
    if hardware.ram_gb >= 8 and hardware.cores >= 4:
        return TIERS[3]
    return TIERS[4]


def pick_model(tier: Tier, installed: list[str], preferred: str = "") -> str:
    names = [n for n in installed if isinstance(n, str)]
    if preferred and preferred in names:
        return preferred
    for candidate in tier.brain_models:
        if candidate in names:
            return candidate
    base = {n.split(":")[0] for n in names}
    for candidate in tier.brain_models:
        if candidate.split(":")[0] in base:
            return next(n for n in names if n.split(":")[0] == candidate.split(":")[0])
    return ""


def resolve(mode: Mode, server_up: bool, local_ready: bool) -> str:
    if mode is Mode.SERVER:
        return "server" if server_up else "none"
    if mode is Mode.LOCAL:
        return "local" if local_ready else "none"
    if server_up:
        return "server"
    return "local" if local_ready else "none"


def describe(hardware: Hardware) -> str:
    return json.dumps({"cores": hardware.cores, "ram_gb": hardware.ram_gb, "gpu": hardware.gpu_name,
                       "vram_gb": hardware.vram_gb}, ensure_ascii=False)
