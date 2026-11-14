import ctypes
import os
import sys

HOST_SCOPES = ("node.host_full", "compute.lease", "agents.run", "mcp.serve", "storage.replica", "inference.host")
BASE = (("microphone", "audio.capture"), ("speaker", "audio.play"), ("camera", "camera.stream"),
        ("sensors", "sensor.read"), ("display", "display.render"), ("edge_inference", "inference.edge"))


def scopes(facts: dict, host_full: bool) -> list[str]:
    found = {"telemetry.report"} | {scope for key, scope in BASE if facts.get(key)}
    if host_full:
        found.update(HOST_SCOPES)
    return sorted(found)


def declare(facts: dict, host_full: bool) -> dict:
    return {"capabilities": [{"scope": scope} for scope in scopes(facts, host_full)],
            "hardware": {"cpu_cores": int(facts.get("cpu_cores", 0)), "ram_mb": int(facts.get("ram_mb", 0))}}


class _Memory(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                ("avail", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong), ("page_avail", ctypes.c_ulonglong),
                ("virtual_total", ctypes.c_ulonglong), ("virtual_avail", ctypes.c_ulonglong),
                ("extended", ctypes.c_ulonglong)]


def ram_mb() -> int:
    if sys.platform == "win32":
        status = _Memory()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total // (1024 * 1024))
        return 0
    try:
        return int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024))
    except (ValueError, OSError, AttributeError):
        return 0


def local_facts(voice: bool) -> dict:
    return {"microphone": bool(voice), "speaker": True, "camera": False, "sensors": False, "display": True,
            "edge_inference": False, "cpu_cores": os.cpu_count() or 0, "ram_mb": ram_mb()}
