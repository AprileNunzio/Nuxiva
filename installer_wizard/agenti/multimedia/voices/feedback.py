"""Short host feedback sounds, independent of browser and neural TTS."""

import io
import math
import struct
import wave
from functools import lru_cache


@lru_cache(maxsize=1)
def wake_wav() -> bytes:
    """Return a quiet, 580 ms rising two-tone cue as mono PCM WAV."""
    rate = 16000
    samples = []
    for i in range(int(rate * 0.58)):
        t = i / rate
        value = 0.0
        for start, duration, frequency, end_frequency, gain in (
            (0.0, 0.32, 420, 1260, 0.16),
            (0.18, 0.4, 1320, 1320, 0.1),
        ):
            elapsed = t - start
            if 0 <= elapsed < duration:
                slope = math.log(end_frequency / frequency) / duration
                phase = frequency * (math.expm1(slope * elapsed) / slope if slope else elapsed)
                envelope = min(1.0, elapsed / 0.008) * (1 - elapsed / duration) ** 2
                value += gain * envelope * math.sin(2 * math.pi * phase)
        samples.append(struct.pack("<h", round(value * 32767)))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"".join(samples))
    return output.getvalue()
