import numpy as np

LEVEL_WINDOW = 0.05


def rms_at(audio: np.ndarray, rate: int, elapsed: float, window: float = LEVEL_WINDOW) -> float:
    start = max(0, int(elapsed * rate))
    chunk = audio[start:start + max(1, int(window * rate))]
    if chunk.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(chunk, dtype=np.float64))))
