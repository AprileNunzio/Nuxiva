import ctypes
import os
import time
from ctypes import wintypes


class _Memory(ctypes.Structure):
    _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD), ("total", ctypes.c_ulonglong),
                ("avail", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong), ("page_avail", ctypes.c_ulonglong),
                ("virtual_total", ctypes.c_ulonglong), ("virtual_avail", ctypes.c_ulonglong),
                ("extended", ctypes.c_ulonglong)]


class _Power(ctypes.Structure):
    _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("percent", ctypes.c_ubyte),
                ("saver", ctypes.c_ubyte), ("life", wintypes.DWORD), ("full", wintypes.DWORD)]


class _Times(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


def _ticks(value: _Times) -> int:
    return (value.high << 32) | value.low


class Sampler:
    def __init__(self) -> None:
        self.cpu_last: tuple[int, int] | None = None
        self.rtt_ms: float | None = None

    def _cpu(self) -> float | None:
        idle, kernel, user = _Times(), _Times(), _Times()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        busy_total, idle_total = _ticks(kernel) + _ticks(user), _ticks(idle)
        previous, self.cpu_last = self.cpu_last, (busy_total, idle_total)
        if previous is None:
            return None
        span = busy_total - previous[0]
        return max(0.0, min(100.0, (span - (idle_total - previous[1])) * 100 / span)) if span > 0 else None

    @staticmethod
    def _ram() -> float | None:
        memory = _Memory(length=ctypes.sizeof(_Memory))
        return float(memory.load) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)) else None

    @staticmethod
    def _battery() -> tuple[float | None, float | None]:
        power = _Power()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power)) or power.percent > 100:
            return None, None
        return float(power.percent), float(power.ac == 1)

    @staticmethod
    def _uptime() -> float:
        return ctypes.windll.kernel32.GetTickCount64() / 1000.0

    @staticmethod
    def _disk() -> float | None:
        free, total = ctypes.c_ulonglong(), ctypes.c_ulonglong()
        root = os.environ.get("SystemDrive", "C:") + "\\"
        if not ctypes.windll.kernel32.GetDiskFreeSpaceExW(root, None, ctypes.byref(total), ctypes.byref(free)) or not total.value:
            return None
        return (total.value - free.value) * 100 / total.value

    def sample(self) -> dict:
        battery, charging = self._battery()
        found = {"cpu": self._cpu(), "ram": self._ram(), "disk": self._disk(), "uptime": self._uptime(),
                 "battery": battery, "charging": charging, "rtt_ms": self.rtt_ms}
        return {key: round(value, 1) for key, value in found.items() if value is not None}

    def timed(self, call):
        started = time.monotonic()
        result = call()
        self.rtt_ms = (time.monotonic() - started) * 1000
        return result
