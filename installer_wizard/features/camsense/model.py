import re

NAME = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
LABEL = re.compile(r"^[a-z0-9][a-z0-9 _-]{0,31}$")
MAX_SENSORS = 40
MAX_LABELS = 8
MAX_SAMPLES = 30
MIN_SIDE = 0.02


class SenseError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def slug(text: str) -> str:
    plain = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:32]
    if not NAME.fullmatch(plain):
        raise SenseError("invalid_name")
    return plain


def label_of(text: str) -> str:
    plain = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not LABEL.fullmatch(plain):
        raise SenseError("invalid_label")
    return plain


def region(value) -> list[float]:
    if value in (None, "", []):
        return [0.0, 0.0, 1.0, 1.0]
    try:
        x, y, w, h = (round(float(v), 4) for v in value)
    except (TypeError, ValueError):
        raise SenseError("invalid_region")
    if min(x, y) < 0 or w < MIN_SIDE or h < MIN_SIDE or x + w > 1.0001 or y + h > 1.0001:
        raise SenseError("invalid_region")
    return [x, y, w, h]
