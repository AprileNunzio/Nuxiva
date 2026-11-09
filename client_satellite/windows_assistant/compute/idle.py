import ctypes
from ctypes import wintypes

IDLE_MILLISECONDS = 5 * 60 * 1000


class LastInputInfo(ctypes.Structure):
    _fields_ = [("size", wintypes.UINT), ("tick", wintypes.DWORD)]


def session_is_idle() -> bool:
    info = LastInputInfo(size=ctypes.sizeof(LastInputInfo))
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return False
    elapsed = (ctypes.windll.kernel32.GetTickCount() - info.tick) & 0xFFFFFFFF
    return IDLE_MILLISECONDS <= elapsed < 0x80000000
