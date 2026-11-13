from __future__ import annotations

import glob
import logging
import re
import shutil
import subprocess
import time
from typing import Any

import psutil

log = logging.getLogger("nuxiva.resources.probe")

GPU_TTL = 5.0
BROWSERS = ("chrome", "chromium", "firefox", "msedge", "brave", "chromium-browser")
MEDIA = ("ffmpeg", "gst-launch-1.0")
_gpu_cache: dict[str, Any] = {"at": 0.0, "value": {"gpu_percent": 0.0, "gpu_mem_total": 0, "gpu_mem_used": 0}}


def _nvidia() -> dict | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        log.info("GPU NVIDIA non letta: %s", exc)
        return None
    rows = [tuple(int(v) for v in re.findall(r"\d+", line)[:3]) for line in out.splitlines() if line.strip()]
    rows = [r for r in rows if len(r) == 3]
    if not rows:
        return None
    return {"gpu_percent": float(max(r[0] for r in rows)), "gpu_mem_used": sum(r[1] for r in rows) * 1048576,
            "gpu_mem_total": sum(r[2] for r in rows) * 1048576}


def _read_int(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return 0


def _sysfs() -> dict | None:
    cards = glob.glob("/sys/class/drm/card[0-9]/device/mem_info_vram_total")
    if not cards:
        return None
    total = used = 0
    busy = 0
    for path in cards:
        base = path.rsplit("/", 1)[0]
        total += _read_int(path)
        used += _read_int(f"{base}/mem_info_vram_used")
        busy = max(busy, _read_int(f"{base}/gpu_busy_percent"))
    return {"gpu_percent": float(min(100, busy)), "gpu_mem_used": used, "gpu_mem_total": total}


def gpu_usage() -> dict:
    now = time.monotonic()
    if now - _gpu_cache["at"] < GPU_TTL:
        return _gpu_cache["value"]
    value = _nvidia() or _sysfs() or {"gpu_percent": 0.0, "gpu_mem_total": 0, "gpu_mem_used": 0}
    _gpu_cache.update(at=now, value=value)
    return value


def system_sample() -> dict:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {"mem_total": int(mem.total), "mem_available": int(mem.available), "swap_total": int(swap.total),
            "swap_used": int(swap.used), "cores": int(psutil.cpu_count() or 0), "cpu_percent": float(psutil.cpu_percent(interval=None)), **gpu_usage()}


def groups(self_pid: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    family = {self_pid}
    try:
        family.update(c.pid for c in psutil.Process(self_pid).children(recursive=True))
    except psutil.Error:
        pass
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            info = proc.info
            name = str(info.get("name") or "").lower()
            mem = info.get("memory_info")
            if mem is None:
                continue
            if info["pid"] in family or "nuxiva" in name:
                key = "nuxiva-core"
            elif name.startswith("ollama"):
                key = "ollama"
            elif any(name.startswith(b) for b in BROWSERS):
                key = "browser"
            elif any(name.startswith(m) for m in MEDIA):
                key = "media"
            else:
                continue
            entry = out.setdefault(key, {"rss": 0, "cpu_percent": 0.0, "count": 0})
            entry["rss"] += int(mem.rss)
            entry["cpu_percent"] += float(info.get("cpu_percent") or 0.0)
            entry["count"] += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return out
