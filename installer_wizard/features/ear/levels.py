import numpy as np

TARGET = 0.06
LOUD = 0.25
QUIET = 0.012
CLIP = 0.985
CLIP_RATIO = 0.02
ATTACK_SMOOTH = 0.25
DECAY = 0.995
MIN_GAIN = 0.25
UTTERANCE_FRAME = 320
SILENCE = 1e-5
GATE_KNEE = 0.005


def voice_floor(noise: float) -> float:
    return max(noise * 2.2, 0.006)


class GainFollower:

    def __init__(self) -> None:
        self.env = 0.0
        self.gain = 1.0

    def follow(self, frame: np.ndarray, rms: float, noise: float, limit: float) -> tuple[np.ndarray, bool]:
        floor = voice_floor(noise)
        voiced = rms > floor
        self.env = max(rms, self.env * DECAY) if voiced else self.env * DECAY
        want = float(np.clip(TARGET / self.env, MIN_GAIN, limit)) if self.env > floor else 1.0
        self.gain += (want - self.gain) * ATTACK_SMOOTH
        if abs(self.gain - 1.0) <= 0.02:
            return frame, voiced
        return np.clip(frame * self.gain, -1.0, 1.0), voiced


def judge(peak_rms: float, clip_ratio: float) -> str:
    if clip_ratio >= CLIP_RATIO or peak_rms >= LOUD:
        return "lower"
    if peak_rms < QUIET:
        return "raise"
    return "ok"


def voiced_rms(x: np.ndarray) -> float:
    frames = x[:len(x) // UTTERANCE_FRAME * UTTERANCE_FRAME].reshape(-1, UTTERANCE_FRAME) if len(x) >= UTTERANCE_FRAME \
        else x.reshape(1, -1)
    energy = np.sqrt((frames ** 2).mean(axis=1))
    voiced = energy[energy > np.percentile(energy, 60)] if len(energy) > 4 else energy
    return float(voiced.mean()) if len(voiced) else 0.0


def utterance_gain(x: np.ndarray, target: float, max_gain: float) -> float:
    rms = voiced_rms(x)
    if rms <= SILENCE:
        return 1.0
    gate = min(1.0, max(0.2, (rms / GATE_KNEE) ** 2))
    return min(max_gain, target / rms) * gate
