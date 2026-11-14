import numpy as np

RATE = 16000
FRAME = 320
START_FRAMES = 4
END_SILENCE_FRAMES = 28
MAX_SECONDS = 25
PRE_FRAMES = 10
MIN_THRESHOLD = 0.012
NOISE_FACTOR = 3.0


def rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame.astype(np.float64) / 32768.0))))


class Segmenter:
    def __init__(self) -> None:
        self.buffer = np.zeros(0, dtype=np.int16)
        self.noise = MIN_THRESHOLD / NOISE_FACTOR
        self.recent: list[np.ndarray] = []
        self.active: list[np.ndarray] = []
        self.voiced = 0
        self.silent = 0
        self.speaking = False

    def threshold(self) -> float:
        return max(MIN_THRESHOLD, self.noise * NOISE_FACTOR)

    def feed(self, pcm: bytes) -> list[bytes]:
        self.buffer = np.concatenate([self.buffer, np.frombuffer(pcm, dtype=np.int16)])
        done = []
        while self.buffer.size >= FRAME:
            frame, self.buffer = self.buffer[:FRAME], self.buffer[FRAME:]
            utterance = self._frame(frame)
            if utterance is not None:
                done.append(utterance)
        return done

    def _frame(self, frame: np.ndarray) -> bytes | None:
        level = rms(frame)
        loud = level > self.threshold()
        if not self.speaking:
            if not loud:
                self.noise += (level - self.noise) * 0.05
            self.recent.append(frame)
            self.recent = self.recent[-PRE_FRAMES:]
            self.voiced = self.voiced + 1 if loud else 0
            if self.voiced >= START_FRAMES:
                self.speaking, self.silent = True, 0
                self.active = list(self.recent)
            return None
        self.active.append(frame)
        self.silent = 0 if loud else self.silent + 1
        if self.silent >= END_SILENCE_FRAMES or len(self.active) * FRAME >= MAX_SECONDS * RATE:
            audio = np.concatenate(self.active).tobytes()
            self.speaking, self.active, self.recent, self.voiced = False, [], [], 0
            return audio
        return None
