import ctypes
import ctypes.wintypes as wt
import logging
import threading

log = logging.getLogger("nuxiva.screenshot.hotkey")

VK_SNAPSHOT = 0x2C
WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
LLKHF_INJECTED = 0x10
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0x4E58
KEY_UP = (WM_KEYUP, WM_SYSKEYUP)
KEY_DOWN = (WM_KEYDOWN, WM_SYSKEYDOWN)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


def decide(code: int, message: int, vk: int, flags: int) -> tuple[bool, bool]:
    if code != HC_ACTION or vk != VK_SNAPSHOT or flags & LLKHF_INJECTED:
        return False, False
    if message in KEY_UP:
        return True, True
    return False, message in KEY_DOWN


class PrintScreenHotkey:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self.ready = threading.Event()
        self.hooked = False
        self.registered = False
        self._proc = None

    @property
    def active(self) -> bool:
        return self.hooked or self.registered

    def start(self) -> bool:
        if self.thread:
            return self.active
        self.thread = threading.Thread(target=self._loop, daemon=True, name="print-screen")
        self.thread.start()
        self.ready.wait(3)
        return self.active

    def _fire(self) -> None:
        try:
            self.callback()
        except Exception:
            log.exception("Gestione del tasto Stamp non riuscita")

    def _bind(self, user32, kernel32):
        lresult = ctypes.c_ssize_t
        hookproc = ctypes.WINFUNCTYPE(lresult, ctypes.c_int, wt.WPARAM, wt.LPARAM)
        user32.SetWindowsHookExW.argtypes = (ctypes.c_int, hookproc, wt.HINSTANCE, wt.DWORD)
        user32.SetWindowsHookExW.restype = wt.HHOOK
        user32.CallNextHookEx.argtypes = (wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM)
        user32.CallNextHookEx.restype = lresult
        user32.UnhookWindowsHookEx.argtypes = (wt.HHOOK,)
        kernel32.GetModuleHandleW.restype = wt.HMODULE

        def proc(code, wparam, lparam):
            info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents if code == HC_ACTION else None
            fire, swallow = decide(code, int(wparam), info.vkCode if info else 0, info.flags if info else 0)
            if fire:
                self._fire()
            if swallow:
                return 1
            return user32.CallNextHookEx(None, code, wparam, lparam)

        self._proc = hookproc(proc)
        return user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)

    def _loop(self) -> None:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()
        hook = self._bind(user32, kernel32)
        self.hooked = bool(hook)
        if not self.hooked:
            log.warning("Hook di tastiera non installato (errore %s)", kernel32.GetLastError())
        self.registered = bool(user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_SNAPSHOT))
        if not self.registered:
            log.info("Tasto Stamp già registrato da un altro programma: resta l'hook di tastiera")
        self.ready.set()
        if not self.active:
            return
        message = wt.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                    self._fire()
        finally:
            if self.registered:
                user32.UnregisterHotKey(None, HOTKEY_ID)
            if hook:
                user32.UnhookWindowsHookEx(hook)

    def stop(self) -> None:
        if self.thread and self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        self.thread = None
        self.hooked = self.registered = False
