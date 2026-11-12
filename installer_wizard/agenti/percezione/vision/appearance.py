from collections import deque

import cv2
import numpy as np

SAMPLE_EVERY = 12
VOTES = 8
MIN_VOTES = 4
MIN_SHARE = 0.6
MIN_CONFIDENCE = 0.6
MIN_INSIDE = 0.6
STRIDE = 3


def classify(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
    out = np.full(h.shape, "", dtype=object)
    chroma = (s >= 45) & (v >= 50)
    out[v < 50] = "black"
    grey = (v >= 50) & (s < 45)
    out[grey & (v > 200)] = "white"
    out[grey & (v <= 200)] = "grey"
    bands = [(0, 8, "red"), (8, 20, "orange"), (20, 33, "yellow"), (33, 85, "green"), (85, 100, "cyan"),
             (100, 130, "blue"), (130, 150, "purple"), (150, 170, "pink"), (170, 181, "red")]
    for lo, hi, name in bands:
        out[chroma & (h >= lo) & (h < hi)] = name
    out[chroma & (h >= 8) & (h < 25) & (v < 140)] = "brown"
    return out


def torso(frame: np.ndarray, box: tuple) -> np.ndarray | None:
    fh, fw = frame.shape[:2]
    x, y, bw, bh = box
    x0, x1 = int(x - 0.3 * bw), int(x + 1.3 * bw)
    y0, y1 = int(y + 1.4 * bh), int(y + 3.0 * bh)
    area = max(1, (x1 - x0) * (y1 - y0))
    cx0, cx1, cy0, cy1 = max(0, x0), min(fw, x1), max(0, y0), min(fh, y1)
    if cx1 <= cx0 or cy1 <= cy0 or (cx1 - cx0) * (cy1 - cy0) / area < MIN_INSIDE:
        return None
    return frame[cy0:cy1:STRIDE, cx0:cx1:STRIDE]


def dominant(frame: np.ndarray, box: tuple) -> tuple[str, float] | None:
    region = torso(frame, box)
    if region is None or region.size == 0:
        return None
    names = classify(cv2.cvtColor(np.ascontiguousarray(region), cv2.COLOR_BGR2HSV)).ravel()
    values, counts = np.unique(names, return_counts=True)
    best = int(np.argmax(counts))
    return str(values[best]), float(counts[best] / names.size)


def observe(track, frame: np.ndarray) -> None:
    if track.frames % SAMPLE_EVERY:
        return
    votes = getattr(track, "attire_votes", None)
    if votes is None:
        votes = track.attire_votes = deque(maxlen=VOTES)
    found = dominant(frame, track.box)
    if found and found[1] >= MIN_SHARE:
        votes.append(found)


def view(track) -> dict | None:
    votes = list(getattr(track, "attire_votes", None) or [])
    if len(votes) < MIN_VOTES:
        return None
    colors = [c for c, _ in votes]
    top = max(set(colors), key=colors.count)
    agreement = colors.count(top) / len(votes)
    share = sum(s for c, s in votes if c == top) / colors.count(top)
    confidence = round(agreement * share, 3)
    return {"color": top, "confidence": confidence} if confidence >= MIN_CONFIDENCE else None
