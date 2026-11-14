import tkinter as tk

import customtkinter as ctk

from autonomy import profile
from i18n.strings import t
from ui import theme

ORDER = (profile.Mode.SERVER, profile.Mode.AUTO, profile.Mode.LOCAL)


class ModeCard:
    def __init__(self, parent, cfg: dict, installed: list[str], hardware: profile.Hardware) -> None:
        self.labels = {mode: t(f"mode.{mode.value}") for mode in ORDER}
        current = profile.parse_mode(cfg.get("mode"))
        tier = profile.recommend(hardware)
        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=10)
        card.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(card, text=t("mode.title"), font=(theme.FONT, 13), text_color=theme.TEXT
                     ).pack(anchor="w", padx=12, pady=(10, 2))
        self.choice = ctk.CTkSegmentedButton(card, values=list(self.labels.values()), selected_color=theme.BLUE)
        self.choice.set(self.labels[current])
        self.choice.pack(anchor="w", padx=12, pady=(0, 4))
        ctk.CTkLabel(card, text=t("mode.hint"), font=(theme.FONT, 11), text_color=theme.DIM, wraplength=420,
                     justify="left").pack(anchor="w", padx=12)
        ctk.CTkLabel(card, text=t("mode.hardware", cores=hardware.cores, ram=hardware.ram_gb,
                                  gpu=hardware.gpu_name or t("mode.no_gpu"), tier=t(f"tier.{tier.name}")),
                     font=(theme.FONT, 11), text_color=theme.DIM, wraplength=420, justify="left"
                     ).pack(anchor="w", padx=12, pady=(6, 0))
        suggested = profile.pick_model(tier, installed) or tier.brain_models[0]
        ctk.CTkLabel(card, text=t("mode.model", model=suggested), font=(theme.FONT, 11), text_color=theme.DIM,
                     wraplength=420, justify="left").pack(anchor="w", padx=12, pady=(2, 0))
        ctk.CTkLabel(card, text=t("mode.model_choice"), font=(theme.FONT, 12), text_color=theme.TEXT
                     ).pack(anchor="w", padx=12, pady=(8, 2))
        self.model = ctk.CTkEntry(card, fg_color=theme.BG, border_color=theme.LINE, placeholder_text=suggested)
        self.model.insert(0, str(cfg.get("local_model") or ""))
        self.model.pack(fill="x", padx=12, pady=(0, 6))
        self.host = tk.BooleanVar(value=bool(cfg.get("host_full")))
        ctk.CTkSwitch(card, text=t("mode.host"), variable=self.host, font=(theme.FONT, 12), text_color=theme.TEXT,
                      progress_color=theme.CYAN).pack(anchor="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(card, text=t("mode.host_hint"), font=(theme.FONT, 11), text_color=theme.DIM, wraplength=420,
                     justify="left").pack(anchor="w", padx=12, pady=(2, 10))

    def values(self) -> dict:
        selected = next((m for m, label in self.labels.items() if label == self.choice.get()), profile.Mode.AUTO)
        return {"mode": selected.value, "local_model": self.model.get().strip()[:80],
                "host_full": bool(self.host.get())}
