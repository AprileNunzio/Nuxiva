import customtkinter as ctk

from i18n.strings import t
from permissions import os_access
from ui import theme


class AccessWindow:
    def __init__(self, root, kind: str) -> None:
        self.kind = kind
        self.window = ctk.CTkToplevel(root, fg_color=theme.PANEL)
        self.window.title(t("access.window"))
        self.window.attributes("-topmost", True)
        self.window.geometry("520x420")
        self.window.minsize(440, 360)
        ctk.CTkLabel(self.window, text=t(f"access.{kind}.title"), font=(theme.FONT, 18, "bold"), text_color=theme.TEXT,
                     wraplength=470, justify="left").pack(anchor="w", padx=24, pady=(22, 8))
        for heading, body in (("access.what", f"access.{kind}.what"), ("access.why", f"access.{kind}.why"),
                              ("access.how", f"access.{kind}.how")):
            ctk.CTkLabel(self.window, text=t(heading), font=(theme.FONT, 11, "bold"), text_color=theme.CYAN
                         ).pack(anchor="w", padx=24, pady=(8, 0))
            ctk.CTkLabel(self.window, text=t(body), font=(theme.FONT, 12), text_color=theme.DIM, wraplength=470,
                         justify="left").pack(anchor="w", padx=24)
        self.status = ctk.CTkLabel(self.window, text="", font=(theme.FONT, 11), text_color=theme.AMBER, wraplength=470,
                                   justify="left")
        self.status.pack(anchor="w", padx=24, pady=(8, 0))
        row = ctk.CTkFrame(self.window, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=16, side="bottom")
        ctk.CTkButton(row, text=t("access.open"), fg_color=theme.BLUE, hover_color=theme.BLUE_HOVER,
                      command=self._open).pack(side="right")
        ctk.CTkButton(row, text=t("access.later"), fg_color=theme.LINE, command=self.window.destroy).pack(side="right", padx=8)

    def _open(self) -> None:
        try:
            os_access.open_settings(self.kind)
        except OSError as exc:
            self.status.configure(text=t("access.open_failed", reason=str(exc), uri=os_access.settings_uri(self.kind)))
            return
        self.window.destroy()
