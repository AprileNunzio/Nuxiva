import time
import tkinter as tk

from ui import theme
from ui.hologram import palette
from ui.hologram.motion import Motion
from ui.hologram.scene import Scene
from ui.hologram.surface import Presenter, animations_enabled

STATE_COLOR = {state: palette.hexcode(state) for state in palette.TONES}
BASE = 112
ACTIVE_MS = 16
REST_MS = 33
CALM_MS = 66
MIN_DELAY_MS = 4
DRAG_THRESHOLD = 4


class Orb:
    def __init__(self, root, scale: float, position: tuple, on_click, on_moved, menu_items) -> None:
        self.root, self.scale, self.on_click, self.on_moved = root, scale, on_click, on_moved
        self.state, self.level, self.hovered = palette.DEFAULT, 0.0, False
        self.size = int(BASE * scale)
        self.motion = Motion(calm=not animations_enabled())
        self.scene = Scene(self.size)
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=theme.TRANSPARENT_KEY)
        self._place(position)
        self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, bg=theme.TRANSPARENT_KEY,
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self._bind()
        self.menu = tk.Menu(self.window, tearoff=0, bg=theme.PANEL, fg=theme.TEXT, activebackground=theme.LINE,
                            activeforeground=theme.TEXT, bd=0)
        self.menu_items = menu_items
        self._drag = (0, 0, 0, 0, False)
        self.presenter = Presenter(self.window, self.canvas, self.size, theme.TRANSPARENT_KEY, theme.BG)
        self._last = time.perf_counter()
        self.root.after(ACTIVE_MS, self._animate)

    def _bind(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag_to)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._menu)
        self.canvas.bind("<Enter>", lambda _event: self._hover(True))
        self.canvas.bind("<Leave>", lambda _event: self._hover(False))

    def _hover(self, inside: bool) -> None:
        self.hovered = inside

    def _place(self, position: tuple) -> None:
        left, top, right, bottom = theme.work_area()
        margin = int(12 * self.scale)
        x = position[0] if position[0] is not None else right - self.size - margin
        y = position[1] if position[1] is not None else bottom - self.size - margin
        x, y = min(max(left, int(x)), right - self.size), min(max(top, int(y)), bottom - self.size)
        self.window.geometry(f"{self.size}x{self.size}+{x}+{y}")

    @property
    def x(self) -> int:
        return self.window.winfo_x()

    @property
    def y(self) -> int:
        return self.window.winfo_y()

    def _press(self, event) -> None:
        self._drag = (event.x_root, event.y_root, self.x, self.y, False)

    def _drag_to(self, event) -> None:
        sx, sy, ox, oy, _moved = self._drag
        if abs(event.x_root - sx) + abs(event.y_root - sy) > DRAG_THRESHOLD:
            self._drag = (sx, sy, ox, oy, True)
            self.window.geometry(f"+{ox + event.x_root - sx}+{oy + event.y_root - sy}")
            self.on_moved(False)

    def _release(self, event) -> None:
        if self._drag[4]:
            self.on_moved(True)
        else:
            self.on_click()

    def _menu(self, event) -> None:
        self.menu.delete(0, "end")
        for item in self.menu_items():
            if item is None:
                self.menu.add_separator()
            elif isinstance(item[1], tk.BooleanVar):
                self.menu.add_checkbutton(label=item[0], variable=item[1], command=item[2])
            else:
                self.menu.add_command(label=item[0], command=item[1])
        self.menu.tk_popup(event.x_root, event.y_root)

    def _interval(self) -> int:
        if self.motion.calm:
            return CALM_MS
        return ACTIVE_MS if self.motion.active or self.hovered else REST_MS

    def _animate(self) -> None:
        now = time.perf_counter()
        dt, self._last = now - self._last, now
        self.motion.step(self.state, self.level, self.hovered, dt)
        self.presenter.present(self.scene.render(self.motion))
        spent = int((time.perf_counter() - now) * 1000)
        self.root.after(max(MIN_DELAY_MS, self._interval() - spent), self._animate)
