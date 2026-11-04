import io
import math
import wave
from array import array

MIN_SECONDS = 0.4
MAX_SECONDS = 6.0
MAX_BYTES = 2 * 1024 * 1024
FLOOR_DB = -120.0


class AudioRejected(ValueError):
    pass


def _db(value: float) -> float:
    return round(20 * math.log10(value), 1) if value > 0 else FLOOR_DB


def analyze(data: bytes) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise AudioRejected("Registrazione vuota o troppo grande")
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
            raw = wav.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise AudioRejected(f"File WAV non valido: {exc}") from exc
    if width != 2 or channels != 1 or not 8000 <= rate <= 48000:
        raise AudioRejected("Serve un WAV mono PCM a 16 bit tra 8 e 48 kHz")
    seconds = frames / rate
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise AudioRejected("La registrazione deve durare tra 0,4 e 6 secondi")
    samples = array("h")
    samples.frombytes(raw[: frames * 2])
    if not samples:
        raise AudioRejected("Registrazione vuota")
    window = max(1, rate // 50)
    levels = []
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        levels.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)) / 32768)
    ordered = sorted(levels)
    noise = ordered[max(0, len(ordered) // 10)]
    speech = ordered[min(len(ordered) - 1, (len(ordered) * 95) // 100)]
    peak = max(abs(s) for s in samples) / 32768
    clipped = sum(1 for s in samples if abs(s) >= 32700) / len(samples)
    snr = round(_db(speech) - _db(noise), 1) if noise > 0 else round(_db(speech) - FLOOR_DB, 1)
    reason = "clipped" if clipped >= 0.01 else "weak" if _db(speech) <= -45 else "noisy" if snr < 10 else ""
    return {"seconds": round(seconds, 2), "sample_rate": rate, "speech_db": _db(speech), "noise_db": _db(noise),
            "peak_db": _db(peak), "snr_db": snr, "clipped_pct": round(clipped * 100, 2), "usable": not reason,
            "reason": reason}
