import native_core

try:
    from agenti.ear import earconf
except ImportError:
    try:
        import earconf
    except ImportError:
        from installer_wizard.agenti.ear import earconf


def config() -> dict:
    end = earconf.number("NUXIVA_EAR_END_SILENCE", 0.65, 0.3, 1.5)
    return {
        "end_silence": end,
        "wake_hold": earconf.number("NUXIVA_EAR_WAKE_HOLD", 1.4, end, 3.0),
        "wake_tail": earconf.number("NUXIVA_EAR_WAKE_TAIL", 0.45, 0.1, 2.0),
        "max_utterance": earconf.number("NUXIVA_EAR_MAX_UTTERANCE", 14.0, 2.0, 60.0),
    }


class PyEndpointer:

    def __init__(self, end_silence: float, wake_hold: float, wake_tail: float, max_utterance: float) -> None:
        self.end_silence = end_silence
        self.wake_hold = max(wake_hold, end_silence)
        self.wake_tail = wake_tail
        self.max_utterance = max_utterance
        self.active = False
        self.start = self.last_voice = self.last_frame = 0.0
        self.woke = False
        self.after_wake = 0.0

    def begin(self, now: float) -> None:
        self.active = True
        self.start = self.last_voice = self.last_frame = now
        self.woke = False
        self.after_wake = 0.0

    def wake(self) -> None:
        if self.active:
            self.woke = True
            self.after_wake = 0.0

    def reset(self) -> None:
        self.active = False
        self.woke = False
        self.after_wake = 0.0

    @property
    def holding(self) -> bool:
        return self.active and self.woke and self.after_wake < self.wake_tail

    def frame(self, now: float, voiced: bool) -> str | None:
        if not self.active:
            return None
        step = min(1.0, max(0.0, now - self.last_frame))
        self.last_frame = now
        if voiced:
            self.last_voice = now
            if self.woke:
                self.after_wake += step
        if now - self.start > self.max_utterance:
            reason = "too_long"
        elif self.holding:
            reason = "wake_hold" if now - self.last_voice > self.wake_hold else None
        else:
            reason = "silence" if now - self.last_voice > self.end_silence else None
        if reason is not None:
            self.reset()
        return reason


def make(**overrides):
    settings = config() | overrides
    engine = native_core.symbol("RustEndpointer")
    if engine is None:
        native_core.python_fallback("ear.endpoint")
        return PyEndpointer(**settings)
    return engine(**settings)
