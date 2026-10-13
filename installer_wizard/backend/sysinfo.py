import os
import shutil
import socket
import subprocess
import time

import psutil

_last_net = {"t": time.time(), "rx": 0, "tx": 0}
_last_gpu = {"t": 0.0, "data": None}


def _primary_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _temperature() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return None
    for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
        if temps.get(key):
            return round(max(t.current for t in temps[key]), 1)
    return None


def _gpu() -> dict:
    now = time.time()
    if _last_gpu["data"] is not None and now - _last_gpu["t"] < 2.5:
        return _last_gpu["data"]

    data = {
        "name": "NUXIVA Accelerated Video/DirectX Core",
        "gpu_percent": 0.0,
        "vram_used": 0.0,
        "vram_total": 0.0,
        "vram_percent": 0.0,
        "temp": None,
        "clock_mhz": None,
        "available": False,
    }

    nvsmi = shutil.which("nvidia-smi")
    if nvsmi:
        try:
            cmd = [
                nvsmi,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks.current.graphics",
                "--format=csv,noheader,nounits",
            ]
            raw = subprocess.check_output(cmd, timeout=1.2).decode("utf-8").strip()
            if raw:
                parts = [p.strip() for p in raw.split(",")]
                if len(parts) >= 6:
                    used = float(parts[2])
                    total = max(float(parts[3]), 1.0)
                    data = {
                        "name": parts[0],
                        "gpu_percent": float(parts[1]),
                        "vram_used": round(used, 1),
                        "vram_total": round(total, 1),
                        "vram_percent": round((used / total) * 100, 1),
                        "temp": float(parts[4]),
                        "clock_mhz": float(parts[5]),
                        "available": True,
                    }
        except Exception:
            pass

    _last_gpu["t"] = now
    _last_gpu["data"] = data
    return data


def _top_processes(limit: int = 8) -> list[dict]:
    procs = []
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                info = p.info
                name = str(info.get("name") or "")
                if not name or name.lower() in ("system idle process", "idle"):
                    continue
                mem_mb = round((info["memory_info"].rss if info.get("memory_info") else 0) / (1024 * 1024), 1)
                cpu = float(info.get("cpu_percent") or 0.0)
                procs.append({
                    "pid": info["pid"],
                    "name": name,
                    "cpu": round(cpu, 1),
                    "mem_mb": mem_mb,
                    "status": str(info.get("status") or "running").lower(),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        return []

    procs.sort(key=lambda x: (x["cpu"], x["mem_mb"]), reverse=True)
    return procs[:limit]


def collect() -> dict:
    net = psutil.net_io_counters()
    now = time.time()
    dt = max(now - _last_net["t"], 0.001)
    rx_rate = (net.bytes_recv - _last_net["rx"]) / dt if _last_net["rx"] else 0
    tx_rate = (net.bytes_sent - _last_net["tx"]) / dt if _last_net["tx"] else 0
    _last_net.update(t=now, rx=net.bytes_recv, tx=net.bytes_sent)

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

    try:
        freq = psutil.cpu_freq()
        cpu_freq = round(freq.current, 1) if freq else None
    except Exception:
        cpu_freq = None

    try:
        per_cpu = [round(x, 1) for x in psutil.cpu_percent(interval=None, percpu=True)]
    except Exception:
        per_cpu = []

    return {
        "hostname": socket.gethostname(),
        "ip": _primary_ip(),
        "uptime": int(now - psutil.boot_time()),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(),
        "cpu_freq": cpu_freq,
        "per_cpu": per_cpu,
        "load": [round(x, 2) for x in load],
        "mem_total": mem.total,
        "mem_used": mem.total - mem.available,
        "mem_percent": mem.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "net_rx_rate": int(max(rx_rate, 0)),
        "net_tx_rate": int(max(tx_rate, 0)),
        "temperature": _temperature(),
        "gpu": _gpu(),
        "top_processes": _top_processes(8),
        "time": now,
    }
