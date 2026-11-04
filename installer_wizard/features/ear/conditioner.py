import numpy as np

try:
    from features.ear import earconf
except ImportError:
    try:
        import earconf
    except ImportError:
        from installer_wizard.features.ear import earconf

RATE = 16000
N_FFT = 512
HOP = N_FFT // 2
WINDOW = np.sqrt(np.hanning(N_FFT + 1)[:-1]).astype(np.float32)
FREQS = np.fft.rfftfreq(N_FFT, 1.0 / RATE)
SMOOTH = 0.7
NOISE_RISE = 1.004
WARMUP = 16
OVER_SUBTRACT = 1.5
NOISE_BIAS = 2.6
GAIN_RELEASE = 0.6
PCM_MAX = 32767 / 32768


class NativeConditioner:

    def __init__(self, highpass_hz: float = 90.0, suppress: bool = True, floor: float = 0.15) -> None:
        self.suppress = suppress
        self.floor = float(np.clip(floor, 0.05, 1.0))
        self.enabled = highpass_hz > 0 or suppress
        if highpass_hz > 0:
            ramp = np.clip((FREQS - highpass_hz * 0.5) / (highpass_hz * 0.5), 0.0, 1.0)
            self.highpass = (np.sin(ramp * np.pi / 2) ** 2).astype(np.float32)
        else:
            self.highpass = np.ones(len(FREQS), dtype=np.float32)
        self.noise: np.ndarray | None = None
        self.smoothed: np.ndarray | None = None
        self.frames = 0
        self.restart()

    @classmethod
    def from_env(cls) -> "NativeConditioner":
        return cls(
            highpass_hz=earconf.number("NUXIVA_EAR_HOST_HIGHPASS_HZ", 90.0, 0.0, 300.0),
            suppress=earconf.flag("NUXIVA_EAR_HOST_NS", True),
            floor=earconf.number("NUXIVA_EAR_HOST_NS_FLOOR", 0.15, 0.05, 1.0),
        )

    def restart(self) -> None:
        self.pending = np.zeros(0, dtype=np.float32)
        self.overlap = np.zeros(HOP, dtype=np.float32)
        self.previous_gain = np.ones(len(FREQS), dtype=np.float32)

    def process(self, pcm: bytes) -> bytes:
        if not isinstance(pcm, (bytes, bytearray, memoryview)) or len(pcm) % 2:
            raise ValueError("Invalid PCM packet")
        if not self.enabled:
            return bytes(pcm)
        if not pcm:
            return b""
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        self.pending = np.concatenate([self.pending, samples])
        produced = []
        start = 0
        while len(self.pending) - start >= N_FFT:
            spectrum = np.fft.rfft(self.pending[start:start + N_FFT] * WINDOW)
            spectrum *= self._gain(spectrum)
            synthesis = np.fft.irfft(spectrum, n=N_FFT).astype(np.float32) * WINDOW
            produced.append(self.overlap + synthesis[:HOP])
            self.overlap = synthesis[HOP:].copy()
            start += HOP
        self.pending = self.pending[start:].copy()
        if not produced:
            return b""
        output = np.clip(np.concatenate(produced), -1.0, PCM_MAX)
        return np.round(output * 32768.0).astype("<i2").tobytes()

    def _gain(self, spectrum: np.ndarray) -> np.ndarray:
        if not self.suppress:
            return self.highpass
        power = (spectrum.real ** 2 + spectrum.imag ** 2).astype(np.float32)
        if self.smoothed is None or self.noise is None:
            self.smoothed = power
            self.noise = power.copy()
        else:
            self.smoothed = SMOOTH * self.smoothed + (1.0 - SMOOTH) * power
            self.noise = np.minimum(self.noise * NOISE_RISE, self.smoothed)
        self.frames += 1
        if self.frames <= WARMUP:
            return self.highpass
        ratio = OVER_SUBTRACT * NOISE_BIAS * self.noise / np.maximum(power, 1e-12)
        gain = np.sqrt(np.maximum(1.0 - ratio, self.floor ** 2)).astype(np.float32)
        gain = np.maximum(gain, self.previous_gain * GAIN_RELEASE)
        self.previous_gain = gain
        return self.highpass * gain
