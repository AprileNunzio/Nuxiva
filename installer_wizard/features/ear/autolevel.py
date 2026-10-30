import numpy as np

from levels import CLIP, GainFollower, judge
from tuning import tuning

WINDOW = 160


class AutoLevel:

    def __init__(self) -> None:
        self.follower = GainFollower()
        self.speech = 0
        self.clipped = 0
        self.peak_rms = 0.0
        self.advice = ""
        self.pending = ""

    @property
    def gain(self) -> float:
        return self.follower.gain

    def apply(self, frame: np.ndarray, rms: float, noise: float) -> np.ndarray:
        leveled, voiced = self.follower.follow(frame, rms, noise, tuning.wake_gain_limit())
        if voiced:
            self._observe(frame, rms)
        return leveled

    def _observe(self, frame: np.ndarray, rms: float) -> None:
        self.speech += 1
        self.peak_rms = max(self.peak_rms, rms)
        if float(np.abs(frame).max()) >= CLIP:
            self.clipped += 1
        if self.speech >= WINDOW:
            self._judge()

    def _judge(self) -> None:
        verdict = judge(self.peak_rms, self.clipped / max(1, self.speech))
        if verdict != self.advice:
            self.advice = verdict
            self.pending = verdict
        self.speech, self.clipped, self.peak_rms = 0, 0, 0.0

    def rejudge(self) -> None:
        self.advice, self.pending = "", ""
        self.speech, self.clipped, self.peak_rms = 0, 0, 0.0

    def take_advice(self) -> str:
        advice, self.pending = self.pending, ""
        return advice

    def status(self) -> dict:
        return {"gain": round(self.gain, 2), "advice": self.advice or "ok"}
