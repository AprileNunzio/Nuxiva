import ctypes
import ctypes.wintypes as wt

from screenshot.sink import AuthError, SinkError, UnreachableError

RESOURCETYPE_DISK = 1
CONNECT_TEMPORARY = 0x4
OK_CODES = frozenset({0, 1219})
AUTH_CODES = frozenset({5, 86, 1326, 1327, 1328, 1329, 1330, 1331, 1907, 1909})
NETWORK_CODES = frozenset({53, 64, 67, 121, 1203, 1222, 1231, 1232, 1311, 2250})


class _NetResource(ctypes.Structure):
    _fields_ = [("dwScope", wt.DWORD), ("dwType", wt.DWORD), ("dwDisplayType", wt.DWORD), ("dwUsage", wt.DWORD),
                ("lpLocalName", wt.LPWSTR), ("lpRemoteName", wt.LPWSTR), ("lpComment", wt.LPWSTR),
                ("lpProvider", wt.LPWSTR)]


def classify(code: int) -> None:
    if code in OK_CODES:
        return
    if code in AUTH_CODES:
        raise AuthError(f"auth:{code}")
    if code in NETWORK_CODES:
        raise UnreachableError(f"network:{code}")
    raise SinkError(f"smb:{code}")


def connect(remote: str, user: str, password: str) -> None:
    mpr = ctypes.windll.mpr
    mpr.WNetAddConnection2W.argtypes = (ctypes.POINTER(_NetResource), wt.LPCWSTR, wt.LPCWSTR, wt.DWORD)
    mpr.WNetAddConnection2W.restype = wt.DWORD
    resource = _NetResource()
    resource.dwType = RESOURCETYPE_DISK
    resource.lpRemoteName = remote
    secret = ctypes.create_unicode_buffer(password)
    try:
        code = mpr.WNetAddConnection2W(ctypes.byref(resource), ctypes.cast(secret, wt.LPCWSTR), user, CONNECT_TEMPORARY)
    finally:
        ctypes.memset(secret, 0, ctypes.sizeof(secret))
    classify(int(code))
