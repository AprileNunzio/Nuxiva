import math
import tkinter as tk

from ui import theme
from ui.flow import Flow

STATE_COLOR = {"idle": "#3b6b8f", "listening": theme.CYAN, "thinking": "#a78bfa", "speaking": theme.GREEN,
               "offline": "#5a6273", "error": theme.RED, "alert": theme.AMBER}
FLOW_STATES = ("listening", "speaking")
FRAME_MS = 33
BASE = 72
CORE = 22


class Orb:
    def __init__(self, root, scale: float, position: tuple, on_click, on_moved, menu_items) -> None:
        self.root, self.scale, self.on_click, self.on_moved = root, scale, on_click, on_moved
        self.state, self.level, self.phase, self.reveal = "idle", 0.0, 0.0, 0.0
        self.flow = Flow()
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=theme.TRANSPARENT_KEY)
        self.window.attributes("-transparentcolor", theme.TRANSPARENT_KEY)
        self.size = int(BASE * scale)
        self._place(position)
        self.canvas = tk.Canvas(self.window, width=self.size, height=self.size, bg=theme.TRANSPARENT_KEY,
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag_to)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._menu)
        self.menu = tk.Menu(self.window, tearoff=0, bg=theme.PANEL, fg=theme.TEXT, activebackground=theme.LINE,
                            activeforeground=theme.TEXT, bd=0)
        self.menu_items = menu_items
        self._drag = (0, 0, 0, 0, False)
        self.root.after(FRAME_MS, self._animate)

    def _place(self, position: tuple) -> None:
        left, top, right, bottom = theme.work_area()
        margin = int(20 * self.scale)
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
        if abs(event.x_root - sx) + abs(event.y_root - sy) > 4:
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

    def _glow(self) -> float:
        if self.state in FLOW_STATES:
            return 4 + 8 * self.flow.amplitude
        if self.state == "thinking":
            return 4
        return 2 + 1.5 * (0.5 + 0.5 * math.sin(self.phase * 0.7))

    def _ribbons(self, center: float, color: str) -> None:
        c, k = self.canvas, self.scale
        reach, height = CORE * 0.84 * k, CORE * 0.62 * k * self.reveal
        shades = (color, theme.mix(theme.BG, color, 0.62), theme.mix(theme.BG, color, 0.38))
        for ribbon, shade, thickness in zip(self.flow.ribbons(self.phase), shades, (2.4, 1.8, 1.4)):
            last = len(ribbon) - 1
            coords = []
            for i, y in enumerate(ribbon):
                coords += [center - reach + 2 * reach * i / last, center + y * height]
            c.create_line(*coords, fill=shade, width=thickness * k, smooth=True, capstyle="round")

    def _animate(self) -> None:
        self.root.after(FRAME_MS, self._animate)
        self.phase += 0.1
        active = self.state in FLOW_STATES
        self.reveal += ((1.0 if active else 0.0) - self.reveal) * 0.22
        self.flow.feed(self.level if active else 0.0)
        c, k, color = self.canvas, self.scale, STATE_COLOR.get(self.state, theme.CYAN)
        center = self.size / 2
        glow = self._glow()
        c.delete("all")
        for ring in range(5, 0, -1):
            r = (CORE + glow * ring / 5) * k
            c.create_oval(center - r, center - r, center + r, center + r,
                          fill=theme.mix(theme.BG, color, 0.10 + 0.08 * (5 - ring)), outline="")
        r = CORE * k
        c.create_oval(center - r, center - r, center + r, center + r, fill=theme.BG, outline=color, width=2 * k)
        if self.state == "thinking":
            for dot in range(3):
                angle = self.phase * 2.4 + dot * 2.094
                px, py = center + 11 * k * math.cos(angle), center + 11 * k * math.sin(angle)
                c.create_oval(px - 3 * k, py - 3 * k, px + 3 * k, py + 3 * k, fill=color, outline="")
        elif self.reveal > 0.02:
            self._ribbons(center, color)
        if self.reveal < 0.98 and self.state != "thinking":
            r = 6 * k * (1.0 - self.reveal)
            c.create_oval(center - r, center - r, center + r, center + r, fill=color, outline="")
