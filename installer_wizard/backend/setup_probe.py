import asyncio
import glob
import logging
import os
import time
from pathlib import Path

log = logging.getLogger("nuxiva.setup")


def _usb_name(device: str) -> str:
    node = Path("/sys/class/video4linux") / Path(device).name / "name"
    try:
        return node.read_text(encoding="utf-8").strip()[:80]
    except OSError:
        return ""


def _capture_nodes() -> list[str]:
    nodes = []
    for device in sorted(glob.glob("/dev/video*")):
        index = Path("/sys/class/video4linux") / Path(device).name / "index"
        try:
            if index.read_text(encoding="utf-8").strip() != "0":
                continue
        except OSError:
            log.info("Indice di %s non leggibile: lo considero un ingresso video", device)
        nodes.append(device)
    return nodes


async def scan_cameras() -> dict:
    from features.cameras import discovery
    started = time.monotonic()
    network: list[dict] = []
    error = ""
    try:
        network = await asyncio.to_thread(discovery.onvif, 2.0)
    except OSError as exc:
        error = str(exc)[:200]
        log.warning("Ricerca ONVIF non riuscita: %s", exc)
    devices = [{"id": f"onvif:{c.get('host', '')}", "name": str(c.get("name") or "")[:80], "type": "onvif",
                "host": str(c.get("host") or "")[:120]} for c in network if c.get("host")]
    devices += [{"id": f"usb:{d}", "name": _usb_name(d), "type": "usb", "host": d} for d in _capture_nodes()]
    return {"devices": devices, "count": len(devices), "scan_ms": round((time.monotonic() - started) * 1000),
            "network_error": error, "at": time.time()}


def server_timezone() -> str:
    tz = os.environ.get("TZ", "")
    if tz:
        return tz
    try:
        target = os.readlink("/etc/localtime")
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    try:
        return Path("/etc/timezone").read_text(encoding="utf-8").strip()
    except OSError:
        return time.tzname[0]


def hardware_report() -> dict:
    import setup_api
    import sysinfo
    gpu = sysinfo._gpu()
    return {**setup_api.hardware(), "gpu_name": gpu.get("name", "") if gpu.get("available") else "",
            "vram_total_gb": round(gpu.get("vram_total", 0) / 1024, 1) if gpu.get("available") else 0,
            "timezone": server_timezone()}
