import io
import logging
import threading
import time
import wave

import numpy as np
import sounddevice as sd

from voice.levels import LEVEL_WINDOW, rms_at

log = logging.getLogger("nuxiva.voice")
SAMPLE_TYPES = {1: np.uint8, 2: np.int16, 4: np.int32}


class Speaker:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.playing = threading.Event()
        self._stop = threading.Event()
        self.level = 0.0

    def play_wav(self, data: bytes, cancelled: threading.Event | None = None) -> None:
        with wave.open(io.BytesIO(data)) as w:
            rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
            frames = w.readframes(w.getnframes())
        dtype = SAMPLE_TYPES[width]
        audio = np.frombuffer(frames, dtype=dtype).astype(np.float32)
        audio = (audio - 128) / 128 if width == 1 else audio / float(np.iinfo(dtype).max)
        self.play(audio.reshape(-1, channels), rate, cancelled)

    def play(self, audio: np.ndarray, rate: int, cancelled: threading.Event | None = None) -> None:
        with self.lock:
            self._stop.clear()
            if cancelled is not None and cancelled.is_set():
                return
            self.playing.set()
            try:
                sd.play(audio, rate)
                started = time.monotonic()
                deadline = len(audio) / rate + 0.3
                while not self._stop.is_set():
                    elapsed = time.monotonic() - started
                    if elapsed >= deadline:
                        break
                    self.level = rms_at(audio, rate, elapsed)
                    self._stop.wait(LEVEL_WINDOW)
                sd.stop()
            except sd.PortAudioError as exc:
                log.warning("Riproduzione non riuscita: %s", exc)
            finally:
                self.level = 0.0
                self.playing.clear()

    def stop(self) -> None:
        self._stop.set()

    def chime(self, rising: bool = True) -> None:
        rate = 44100
        notes = (659.25, 987.77) if rising else (987.77, 659.25)
        parts = []
        for frequency in notes:
            t = np.arange(int(rate * 0.09)) / rate
            envelope = np.minimum(1, t * 80) * np.exp(-t * 18)
            parts.append(0.18 * envelope * np.sin(2 * np.pi * frequency * t))
        threading.Thread(target=self.play, args=(np.concatenate(parts).astype(np.float32), rate), daemon=True).start()
