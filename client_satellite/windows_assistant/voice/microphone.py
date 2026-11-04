import logging

import numpy as np
import sounddevice as sd

from voice.cleaner import AudioCleaner, MediaState

log = logging.getLogger("nuxiva.voice")
RATE = 16000
BLOCK = 1600


class Microphone:
    def __init__(self, on_pcm, device=None) -> None:
        self.on_pcm, self.device = on_pcm, device
        self.stream = None
        self.muted = False
        self.level = 0.0
        self.error = ""
        self._ratio = 1.0
        self.cleaner = AudioCleaner()
        self.media_state = MediaState()

    def set_media_state(self, is_active: bool, source_id: str = "", volume: float = 0.0) -> None:
        self.media_state = MediaState(is_active=is_active, source_id=source_id, volume_normalized=volume)

    def start(self) -> None:
        self.stop()
        try:
            self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK,
                                         device=self.device, callback=self._native)
            self.stream.start()
            self.error = ""
            return
        except sd.PortAudioError as exc:
            log.info("16 kHz non supportati dal microfono (%s): ricampionamento", exc)
        try:
            rate = int(sd.query_devices(self.device, "input")["default_samplerate"])
            self._ratio = RATE / rate
            self.stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=int(rate / 10),
                                         device=self.device, callback=self._resample)
            self.stream.start()
            self.error = ""
        except (sd.PortAudioError, ValueError) as exc:
            self.stream, self.error = None, f"Microfono non disponibile: {exc}"
            log.warning(self.error)

    def stop(self) -> None:
        if self.stream is None:
            return
        self.stream.stop()
        self.stream.close()
        self.stream = None

    def _emit(self, pcm16: np.ndarray) -> None:
        raw_bytes = pcm16.tobytes()
        clean_bytes, is_gated, level = self.cleaner.clean_frame(raw_bytes, self.media_state)
        self.level = level
        if not self.muted and not is_gated:
            self.on_pcm(clean_bytes)

    def _native(self, data, frames, moment, status) -> None:
        self._emit(data[:, 0].copy())

    def _resample(self, data, frames, moment, status) -> None:
        source = data[:, 0]
        count = max(1, int(round(len(source) * self._ratio)))
        out = np.interp(np.linspace(0, len(source) - 1, count), np.arange(len(source)), source)
        self._emit((np.clip(out, -1, 1) * 32767).astype("<i2"))
