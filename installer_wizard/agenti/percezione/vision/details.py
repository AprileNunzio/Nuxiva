import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

import appearance

sys.path.append(str(Path(__file__).resolve().parents[1] / "biometrics"))
import face_engine

SAMPLE_EVERY = 2.0
MIN_SAMPLES = 4
MIN_FACE_PX = 80
CIGARETTE_HIT = 0.6
HAIR_SHARE = 0.4
HAIR = frozenset({"black", "brown", "grey", "white", "red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink"})


def hair_color(frame: np.ndarray, box: tuple) -> str | None:
    fh, fw = frame.shape[:2]
    x, y, bw, bh = (float(v) for v in box)
    x0, x1 = max(0, int(x + 0.2 * bw)), min(fw, int(x + 0.8 * bw))
    y0, y1 = max(0, int(y - 0.25 * bh)), min(fh, int(y + 0.05 * bh))
    if x1 - x0 < 8 or y1 - y0 < 4:
        return None
    region = np.ascontiguousarray(frame[y0:y1:2, x0:x1:2])
    names = appearance.classify(cv2.cvtColor(region, cv2.COLOR_BGR2HSV)).ravel()
    values, counts = np.unique(names, return_counts=True)
    best = int(np.argmax(counts))
    color = str(values[best])
    return color if color in HAIR and counts[best] / names.size >= HAIR_SHARE else None


def observe(track, frame: np.ndarray, slug: str, now: float) -> None:
    if track.detail_slug != slug:
        track.details.clear()
        track.detail_slug = slug
    if track.aligned is None or track.live_state == "spoof" or not track.facing or track.box[2] < MIN_FACE_PX:
        return
    if now - track.detail_at < SAMPLE_EVERY:
        return
    found = face_engine.traits_of(track.aligned)
    if found is None:
        return
    track.detail_at = now
    found["hair"] = hair_color(frame, track.box)
    track.details.append(found)


def view(track) -> dict | None:
    rows = list(track.details)
    if len(rows) < MIN_SAMPLES:
        return None
    hairs = Counter(r["hair"] for r in rows if r.get("hair"))
    out = {k: round(float(np.mean([r[k] for r in rows])), 3) for k in ("glasses", "beard", "fringe")}
    out.update(samples=len(rows), hair=hairs.most_common(1)[0][0] if hairs else None, at=track.detail_at,
               cigarette=round(sum(r["cigarette"] >= CIGARETTE_HIT for r in rows) / len(rows), 3))
    return out
