import ctypes
import logging
import sys

import numpy as np

log = logging.getLogger("nuxiva.hologram")

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
ULW_ALPHA = 0x02
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
BI_RGB = 0
DIB_RGB_COLORS = 0
SPI_GETCLIENTAREAANIMATION = 0x1042
KEY_THRESHOLD = 24


def animations_enabled() -> bool:
    if sys.platform != "win32":
        return True
    flag = ctypes.c_int(1)
    if not ctypes.windll.user32.SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(flag), 0):
        return True
    return bool(flag.value)


class LayeredSurface:
    def __init__(self, window, size: int) -> None:
        import ctypes.wintypes as wt

        self.wt, self.size = wt, size
        self.screen = self.memory = self.bitmap = self.previous = None
        self.user32, self.gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        self._signatures()
        window.update_idletasks()
        self.hwnd = self.user32.GetParent(window.winfo_id()) or window.winfo_id()
        style = self.user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        self.user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED)
        self.screen = self.user32.GetDC(None)
        self.memory = self.gdi32.CreateCompatibleDC(self.screen)
        self.bits = ctypes.c_void_p()
        header = _BitmapInfo()
        header.biSize = ctypes.sizeof(_BitmapInfo)
        header.biWidth, header.biHeight, header.biPlanes = size, -size, 1
        header.biBitCount, header.biCompression = 32, BI_RGB
        self.bitmap = self.gdi32.CreateDIBSection(self.memory, ctypes.byref(header), DIB_RGB_COLORS,
                                                  ctypes.byref(self.bits), None, 0)
        if not self.bitmap or not self.bits:
            self.close()
            raise ctypes.WinError()
        self.previous = self.gdi32.SelectObject(self.memory, self.bitmap)
        self.blend = _Blend(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        self.extent = wt.SIZE(size, size)
        self.origin = wt.POINT(0, 0)

    def _signatures(self) -> None:
        wt, u, g = self.wt, self.user32, self.gdi32
        handle = ctypes.c_void_p
        u.GetParent.argtypes, u.GetParent.restype = [handle], handle
        u.GetWindowLongPtrW.argtypes, u.GetWindowLongPtrW.restype = [handle, ctypes.c_int], ctypes.c_ssize_t
        u.SetWindowLongPtrW.argtypes = [handle, ctypes.c_int, ctypes.c_ssize_t]
        u.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.GetDC.argtypes, u.GetDC.restype = [handle], handle
        u.ReleaseDC.argtypes = [handle, handle]
        u.UpdateLayeredWindow.argtypes = [handle, handle, ctypes.c_void_p, ctypes.POINTER(wt.SIZE), handle,
                                          ctypes.POINTER(wt.POINT), wt.DWORD, ctypes.POINTER(_Blend), wt.DWORD]
        u.UpdateLayeredWindow.restype = wt.BOOL
        g.CreateCompatibleDC.argtypes, g.CreateCompatibleDC.restype = [handle], handle
        g.CreateDIBSection.argtypes = [handle, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                       handle, wt.DWORD]
        g.CreateDIBSection.restype = handle
        g.SelectObject.argtypes, g.SelectObject.restype = [handle, handle], handle
        g.DeleteObject.argtypes, g.DeleteDC.argtypes = [handle], [handle]

    def present(self, frame: bytes) -> None:
        if len(frame) != self.size * self.size * 4:
            raise ValueError("hologram frame size mismatch")
        ctypes.memmove(self.bits, frame, len(frame))
        if not self.user32.UpdateLayeredWindow(self.hwnd, self.screen, None, ctypes.byref(self.extent), self.memory,
                                               ctypes.byref(self.origin), 0, ctypes.byref(self.blend), ULW_ALPHA):
            raise ctypes.WinError()

    def close(self) -> None:
        if self.previous:
            self.gdi32.SelectObject(self.memory, self.previous)
            self.previous = None
        if self.bitmap:
            self.gdi32.DeleteObject(self.bitmap)
            self.bitmap = None
        if self.memory:
            self.gdi32.DeleteDC(self.memory)
            self.memory = None
        if self.screen:
            self.user32.ReleaseDC(None, self.screen)
            self.screen = None


class KeyedSurface:
    def __init__(self, window, canvas, size: int, key: str, backdrop: str) -> None:
        from PIL import Image, ImageTk

        self.image, self.photo_type = Image, ImageTk.PhotoImage
        self.canvas, self.size = canvas, size
        window.attributes("-transparentcolor", key)
        self.key = np.array([int(key[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
        self.backdrop = np.array([int(backdrop[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
        self.photo = None
        self.item = canvas.create_image(0, 0, anchor="nw")

    def present(self, frame: bytes) -> None:
        pixels = np.frombuffer(frame, dtype=np.uint8).reshape(self.size, self.size, 4).astype(np.float32)
        alpha = pixels[..., 3:4] / 255.0
        rgb = pixels[..., [2, 1, 0]] + self.backdrop * (1.0 - alpha)
        rgb = np.where(pixels[..., 3:4] < KEY_THRESHOLD, self.key, rgb)
        self.photo = self.photo_type(self.image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB"))
        self.canvas.itemconfigure(self.item, image=self.photo)

    def close(self) -> None:
        self.photo = None


class _BitmapInfo(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32), ("bmiColors", ctypes.c_uint32)]


class _Blend(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte), ("SourceConstantAlpha", ctypes.c_ubyte),
                ("AlphaFormat", ctypes.c_ubyte)]


class Presenter:
    def __init__(self, window, canvas, size: int, key: str, backdrop: str) -> None:
        self.window, self.canvas, self.size, self.key, self.backdrop = window, canvas, size, key, backdrop
        self.surface = self._open()

    @property
    def layered(self) -> bool:
        return isinstance(self.surface, LayeredSurface)

    def _open(self):
        if sys.platform == "win32":
            try:
                return LayeredSurface(self.window, self.size)
            except OSError:
                log.exception("Superficie a trasparenza reale non disponibile, uso il colore chiave")
        return self._keyed()

    def _keyed(self) -> KeyedSurface:
        return KeyedSurface(self.window, self.canvas, self.size, self.key, self.backdrop)

    def present(self, frame: bytes) -> None:
        if not self.layered:
            self.surface.present(frame)
            return
        try:
            self.surface.present(frame)
        except OSError:
            log.exception("Aggiornamento della finestra a strati fallito, passo al colore chiave")
            self.surface.close()
            self.surface = self._keyed()
            self.surface.present(frame)

    def close(self) -> None:
        self.surface.close()
