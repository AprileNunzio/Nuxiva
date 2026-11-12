import math
import os
from dataclasses import dataclass
from typing import Callable, Mapping

import numpy as np

RATE = 16000
GAIN_DB_MIN, GAIN_DB_MAX = -12.0, 12.0
HIGHPASS_MIN, HIGHPASS_MAX = 0.0, 300.0
LOW_SHELF_HZ = 220.0
MID_CENTER_HZ = 1200.0
MID_WIDTH_OCT = 0.9
HIGH_SHELF_HZ = 3800.0
PEAK = 0.97
PAD = 4096
KEYS = {
    "enabled": "NUXIVA_EAR_EQ",
    "highpass_hz": "NUXIVA_EAR_EQ_HIGHPASS",
    "low_db": "NUXIVA_EAR_EQ_LOW",
    "mid_db": "NUXIVA_EAR_EQ_MID",
    "high_db": "NUXIVA_EAR_EQ_HIGH",
}

Getter = Callable[[str, str], str]


def _bounded(raw: object, default: float, lo: float, hi: float) -> float:
    try:
        value = float(str(raw).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value)) if math.isfinite(value) else default


def _flag(raw: object) -> bool:
    return str(raw).strip().lower() in ("1", "on", "yes", "true")


@dataclass(frozen=True, slots=True)
class EqSettings:
    enabled: bool = False
    highpass_hz: float = 0.0
    low_db: float = 0.0
    mid_db: float = 0.0
    high_db: float = 0.0

    @classmethod
    def build(cls, enabled: object, highpass_hz: object, low_db: object, mid_db: object, high_db: object) -> "EqSettings":
        return cls(
            enabled=enabled if isinstance(enabled, bool) else _flag(enabled),
            highpass_hz=_bounded(highpass_hz, 0.0, HIGHPASS_MIN, HIGHPASS_MAX),
            low_db=_bounded(low_db, 0.0, GAIN_DB_MIN, GAIN_DB_MAX),
            mid_db=_bounded(mid_db, 0.0, GAIN_DB_MIN, GAIN_DB_MAX),
            high_db=_bounded(high_db, 0.0, GAIN_DB_MIN, GAIN_DB_MAX),
        )

    @classmethod
    def from_source(cls, get: Getter) -> "EqSettings":
        return cls.build(*(get(KEYS[field], "0") for field in ("enabled", "highpass_hz", "low_db", "mid_db", "high_db")))

    @classmethod
    def from_env(cls) -> "EqSettings":
        return cls.from_source(lambda key, default: os.environ.get(key, default))

    @classmethod
    def from_mapping(cls, values: Mapping[str, object], fallback: "EqSettings") -> "EqSettings":
        return cls.build(*(values.get(field, getattr(fallback, field))
                           for field in ("enabled", "highpass_hz", "low_db", "mid_db", "high_db")))

    @property
    def active(self) -> bool:
        return self.enabled and (self.highpass_hz > 0 or any(abs(v) >= 0.1 for v in (self.low_db, self.mid_db, self.high_db)))

    def as_dict(self) -> dict:
        return {"enabled": self.enabled, "highpass_hz": round(self.highpass_hz, 1), "low_db": round(self.low_db, 1),
                "mid_db": round(self.mid_db, 1), "high_db": round(self.high_db, 1)}


def response(settings: EqSettings, freqs: np.ndarray) -> np.ndarray:
    f = np.maximum(np.asarray(freqs, dtype=np.float64), 1.0)
    low = 1.0 / (1.0 + (f / LOW_SHELF_HZ) ** 2)
    high = 1.0 / (1.0 + (HIGH_SHELF_HZ / f) ** 2)
    mid = np.exp(-0.5 * (np.log2(f / MID_CENTER_HZ) / MID_WIDTH_OCT) ** 2)
    gain = 10.0 ** ((settings.low_db * low + settings.mid_db * mid + settings.high_db * high) / 20.0)
    if settings.highpass_hz > 0:
        gain = gain / np.sqrt(1.0 + (settings.highpass_hz / f) ** 4)
    return gain


def apply(samples: np.ndarray, settings: EqSettings) -> np.ndarray:
    x = np.asarray(samples, dtype=np.float32)
    if not settings.active or x.size < 2:
        return x
    size = 1 << int(math.ceil(math.log2(x.size + PAD)))
    spectrum = np.fft.rfft(x, n=size)
    spectrum *= response(settings, np.fft.rfftfreq(size, 1.0 / RATE))
    y = np.fft.irfft(spectrum, n=size)[:x.size]
    return (PEAK * np.tanh(y / PEAK)).astype(np.float32)

