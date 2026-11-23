import numpy as np

TONES = {
    "idle": (0x3f, 0xa9, 0xff),
    "listening": (0x29, 0xe0, 0xff),
    "thinking": (0xa7, 0x8b, 0xfa),
    "speaking": (0x3d, 0xff, 0xa8),
    "offline": (0x5a, 0x62, 0x73),
    "error": (0xff, 0x6b, 0x81),
    "alert": (0xff, 0xb5, 0x47),
}
DEFAULT = "idle"
DEEP = np.array((0x05, 0x0b, 0x18), dtype=np.float32) / 255.0
GLASS = np.array((0x0b, 0x16, 0x2c), dtype=np.float32) / 255.0
WHITE = np.ones(3, dtype=np.float32)


def known(state: str) -> str:
    return state if state in TONES else DEFAULT


def tone(state: str) -> np.ndarray:
    return np.array(TONES[known(state)], dtype=np.float32) / 255.0


def hexcode(state: str) -> str:
    return "#" + "".join(f"{c:02x}" for c in TONES[known(state)])


def lift(color: np.ndarray, amount: float) -> np.ndarray:
    return color + (WHITE - color) * amount
