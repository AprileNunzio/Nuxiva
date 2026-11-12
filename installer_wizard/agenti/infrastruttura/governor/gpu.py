import glob
import logging
import re
import shutil
import subprocess
import time

import psutil

log = logging.getLogger("nuxiva.governor")
DISCRETE = re.compile(r"nvidia|geforce|quadro|rtx|gtx|radeon\s*(rx|pro|vii)|\barc\s*a\d|tesla", re.I)
SOFTWARE = re.compile(r"llvmpipe|swiftshader|softpipe|software|microsoft basic", re.I)
LOW_POWER = re.compile(r"mali|adreno|powervr|videocore|vivante|tegra|lima|panfrost", re.I)
RENDERER = re.compile(r"^[\w\s().,/+:;@#\-]{0,160}$")
BUDGETS = ((512, 6), (1024, 10), (2048, 16), (4096, 24), (8192, 36))
TOP_BUDGET = 48
TIER_FACTOR = {"full": 1.0, "reduced": 0.6, "minimal": 0.35}
SIZE_WEIGHT = {"s": 1.0, "m": 2.0, "l": 3.0, "full": 4.0}
CACHE_SECONDS = 600.0


def _nvidia() -> int:
    if not shutil.which("nvidia-smi"):
        return 0
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=4, check=False).stdout
        return max((int(v) for v in re.findall(r"\d+", out)), default=0)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        log.info("Memoria della GPU NVIDIA non letta: %s", exc)
        return 0


def _sysfs() -> int:
    best = 0
    for path in glob.glob("/sys/class/drm/card*/device/mem_info_vram_total"):
        try:
            with open(path, encoding="utf-8") as f:
                best = max(best, int(f.read().strip()) // 1048576)
        except (OSError, ValueError):
            continue
    return best


class LocalGpu:
    def __init__(self) -> None:
        self.cached: dict | None = None
        self.at = 0.0

    def read(self) -> dict:
        now = time.time()
        if self.cached is not None and now - self.at < CACHE_SECONDS:
            return self.cached
        vram = _nvidia() or _sysfs()
        shared = not vram
        if shared:
            vram = int(psutil.virtual_memory().total / 1048576 / 4)
        self.cached, self.at = {"vram_mb": vram, "shared": shared, "source": "server"}, now
        return self.cached


local_gpu = LocalGpu()


def clean_gpu(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    renderer = str(raw.get("renderer") or "")[:160]
    out = {"renderer": renderer if RENDERER.match(renderer) else ""}
    for key, lo, hi in (("device_memory", 0, 64), ("cores", 0, 256), ("max_texture", 0, 65536), ("pixels", 0, 80_000_000)):
        try:
            out[key] = max(lo, min(hi, float(raw.get(key) or 0)))
        except (TypeError, ValueError):
            out[key] = 0
    out["webgpu"] = raw.get("webgpu") is True
    return out


def estimate(gpu: dict) -> dict:
    renderer = gpu.get("renderer", "")
    ram_mb = (gpu.get("device_memory") or 4) * 1024
    if SOFTWARE.search(renderer):
        vram, kind = 256, "software"
    elif DISCRETE.search(renderer):
        vram, kind = max(4096, int(ram_mb / 2)), "discrete"
    elif LOW_POWER.search(renderer):
        vram, kind = int(min(1024, ram_mb / 4)), "mobile"
    else:
        vram, kind = int(min(2048, ram_mb / 4)), "integrated"
    if gpu.get("max_texture", 0) and gpu["max_texture"] < 8192:
        vram = min(vram, 768)
    if gpu.get("pixels", 0) > 8_000_000:
        vram = int(vram * 0.8)
    return {"vram_mb": vram, "kind": kind, "source": "browser"}


def budget(vram_mb: float, tier: str, busy: bool) -> int:
    base = next((b for limit, b in BUDGETS if vram_mb <= limit), TOP_BUDGET)
    value = base * TIER_FACTOR.get(tier, 1.0) * (0.8 if busy else 1.0)
    return max(2, int(round(value)))


def weight(declared, size: str, measured_ms: float | None) -> float:
    base = SIZE_WEIGHT.get(size, 2.0)
    if isinstance(declared, dict):
        try:
            base = max(0.5, min(8.0, float(declared.get("gpu", base)) * 0.7 + float(declared.get("cpu", base)) * 0.3))
        except (TypeError, ValueError):
            pass
    if measured_ms:
        base += min(3.0, measured_ms / 8.0)
    return round(base, 2)
