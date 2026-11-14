import ctypes
import ctypes.wintypes as wt
import threading

VK_SNAPSHOT = 0x2C
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0x4E58


class PrintScreenHotkey:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self.ready = threading.Event()
        self.registered = False

    def start(self) -> bool:
        if self.thread:
            return self.registered
        self.thread = threading.Thread(target=self._loop, daemon=True, name="print-screen")
        self.thread.start()
        self.ready.wait(3)
        return self.registered

    def _loop(self) -> None:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()
        self.registered = bool(user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_SNAPSHOT))
        self.ready.set()
        if not self.registered:
            return
        message = wt.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                    self.callback()
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

    def stop(self) -> None:
        if self.thread and self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        self.thread = None
        self.registered = False
