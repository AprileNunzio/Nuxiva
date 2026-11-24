import ctypes
import ctypes.wintypes as wt
import io

CF_DIB = 8
GMEM_MOVEABLE = 0x0002
BMP_HEADER = 14


class ClipboardError(OSError):
    pass


def dib(image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "BMP")
    return buffer.getvalue()[BMP_HEADER:]


def _api():
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes, kernel32.GlobalAlloc.restype = (wt.UINT, ctypes.c_size_t), wt.HGLOBAL
    kernel32.GlobalLock.argtypes, kernel32.GlobalLock.restype = (wt.HGLOBAL,), ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = (wt.HGLOBAL,)
    kernel32.GlobalFree.argtypes = (wt.HGLOBAL,)
    user32.SetClipboardData.argtypes, user32.SetClipboardData.restype = (wt.UINT, wt.HANDLE), wt.HANDLE
    user32.OpenClipboard.argtypes = (wt.HWND,)
    return user32, kernel32


def copy(image) -> None:
    data = dib(image)
    user32, kernel32 = _api()
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise ClipboardError("alloc")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise ClipboardError("lock")
    ctypes.memmove(pointer, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise ClipboardError("open")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_DIB, handle):
            kernel32.GlobalFree(handle)
            raise ClipboardError("set")
    finally:
        user32.CloseClipboard()
