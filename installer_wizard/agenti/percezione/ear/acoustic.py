from types import SimpleNamespace

import numpy as np

RATE = 16000
PAD_BEFORE_S = 0.2
PAD_AFTER_S = 0.35
TOLERANCE_S = 0.15
MIN_SUPPORT = 0.3
MAX_SPANS = 64


def spans(timestamps: list | None) -> list[tuple[float, float]]:
    out = []
    for item in (timestamps or [])[:MAX_SPANS]:
        if not isinstance(item, dict):
            continue
        start, end = item.get("start"), item.get("end")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start >= 0:
            out.append((start / RATE, end / RATE))
    return out


def trim(audio: np.ndarray, voiced: list[tuple[float, float]]) -> tuple[np.ndarray, float]:
    if not voiced:
        return audio, 0.0
    first = max(0, int((voiced[0][0] - PAD_BEFORE_S) * RATE))
    last = min(len(audio), int((voiced[-1][1] + PAD_AFTER_S) * RATE))
    if last - first < RATE * 0.2:
        return audio, 0.0
    return audio[first:last], first / RATE


def support(start: float, end: float, voiced: list[tuple[float, float]]) -> float:
    length = max(end - start, 0.02)
    covered = sum(max(0.0, min(end, b + TOLERANCE_S) - max(start, a - TOLERANCE_S)) for a, b in voiced)
    return min(1.0, covered / length)


def _number(value, default: float) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def ground(segments: list, voiced: list[tuple[float, float]], offset: float) -> tuple[list, list[str]]:
    if not voiced:
        return segments, []
    kept_segments, dropped = [], []
    for segment in segments:
        words = getattr(segment, "words", None)
        if not isinstance(words, (list, tuple)) or not words:
            kept_segments.append(segment)
            continue
        kept = []
        for word in words:
            start = _number(getattr(word, "start", None), -1.0)
            end = _number(getattr(word, "end", None), -1.0)
            if start < 0 or end < start or support(start + offset, end + offset, voiced) >= MIN_SUPPORT:
                kept.append(word)
            else:
                dropped.append(str(getattr(word, "word", "")).strip())
        if len(kept) == len(words):
            kept_segments.append(segment)
        elif kept:
            kept_segments.append(SimpleNamespace(
                text="".join(str(getattr(w, "word", "")) for w in kept).strip(), words=kept,
                avg_logprob=_number(getattr(segment, "avg_logprob", None), 0.0),
                no_speech_prob=_number(getattr(segment, "no_speech_prob", None), 0.0),
                compression_ratio=_number(getattr(segment, "compression_ratio", None), 1.0),
                start=_number(getattr(segment, "start", None), 0.0), end=_number(getattr(segment, "end", None), 0.0)))
    return kept_segments, dropped
