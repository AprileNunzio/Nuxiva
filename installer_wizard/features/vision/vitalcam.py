import re
import threading
import time
from collections import deque

import cv2
import numpy as np

import pulse
import selection

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
TARGET_TTL = 4.0
MAX_TARGETS = 4
HEART_WINDOW = 12.0
BREATH_WINDOW = 32.0
SAMPLE_GAP = 1.0 / 32
ESTIMATE_EVERY = 2.0
TRACK_FRESH = 0.6
CHEST_SIZE = (64, 32)
STEP_LIMIT = 0.12
ANCHOR_SHIFT = 0.15
ANCHOR_SCALE = 0.2
FACE_JUMP = 0.2
MIN_EYES = 20.0
HEART_MIN_QUALITY = 0.3
BREATH_MIN_QUALITY = 0.6
AGREE = 3
HEART_SPREAD = 6
BREATH_SPREAD = 2


def _patch_mean(frame: np.ndarray, center: np.ndarray, half_w: float, half_h: float) -> tuple[np.ndarray, int] | None:
    height, width = frame.shape[:2]
    x0, x1 = int(center[0] - half_w), int(center[0] + half_w)
    y0, y1 = int(center[1] - half_h), int(center[1] + half_h)
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height or x1 - x0 < 4 or y1 - y0 < 3:
        return None
    patch = frame[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
    return patch.mean(axis=0), patch.shape[0]


def face_rgb(frame: np.ndarray, face) -> np.ndarray | None:
    if frame is None or frame.ndim != 3 or face is None:
        return None
    right_eye, left_eye, _, right_mouth, left_mouth = (np.array([float(face[4 + 2 * i]), float(face[5 + 2 * i])]) for i in range(5))
    eyes = float(np.linalg.norm(left_eye - right_eye))
    if eyes < MIN_EYES:
        return None
    outward = (right_eye - left_eye) / eyes
    middle = (right_eye + left_eye) / 2
    regions = (
        (middle - np.array([0.0, 0.55 * eyes]), 0.35 * eyes, 0.15 * eyes),
        ((right_eye + right_mouth) / 2 + outward * 0.1 * eyes, 0.15 * eyes, 0.15 * eyes),
        ((left_eye + left_mouth) / 2 - outward * 0.1 * eyes, 0.15 * eyes, 0.15 * eyes),
    )
    parts = [p for p in (_patch_mean(frame, c, w, h) for c, w, h in regions) if p is not None]
    if len(parts) < 2:
        return None
    total = sum(n for _, n in parts)
    return (sum(m * n for m, n in parts) / total)[::-1]


class ChestMotion:

    def __init__(self) -> None:
        self.window = cv2.createHanningWindow(CHEST_SIZE, cv2.CV_32F)
        self.reset()

    def reset(self) -> None:
        self.anchor: tuple[int, int, int, int] | None = None
        self.region: tuple[int, int, int, int] | None = None
        self.reference: np.ndarray | None = None
        self.position = 0.0

    def _moved(self, box) -> bool:
        x, y, bw, bh = box
        ax, ay, aw, ah = self.anchor
        shift = np.hypot((x + bw / 2) - (ax + aw / 2), (y + bh / 2) - (ay + ah / 2))
        return shift > ANCHOR_SHIFT * aw or abs(bw - aw) > ANCHOR_SCALE * aw

    def _place(self, box, width: int, height: int) -> tuple[int, int, int, int] | None:
        x, y, bw, bh = box
        center = x + bw / 2
        x0, x1 = int(max(0, center - 1.1 * bw)), int(min(width, center + 1.1 * bw))
        y0 = int(y + 1.15 * bh)
        y1 = int(min(height, y0 + 0.9 * bh))
        return (x0, y0, x1, y1) if x1 - x0 >= 24 and y1 - y0 >= 12 else None

    def update(self, frame: np.ndarray, box) -> float | None:
        if self.anchor is None or self._moved(box):
            self.reset()
            self.anchor = tuple(int(v) for v in box)
            self.region = self._place(box, frame.shape[1], frame.shape[0])
            return None
        if self.region is None:
            return None
        x0, y0, x1, y1 = self.region
        roi = frame[y0:y1, x0:x1]
        gray = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, CHEST_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)
        if self.reference is None:
            self.reference = small
            return 0.0
        (_, dy), _ = cv2.phaseCorrelate(self.reference.copy(), small, self.window.copy())
        position = float(dy) * (y1 - y0) / CHEST_SIZE[1] / max(1.0, float(self.anchor[3]))
        if abs(position - self.position) > STEP_LIMIT:
            self.reset()
            return None
        self.position = position
        return position


class PersonMeter:

    def __init__(self) -> None:
        self.colors: deque = deque(maxlen=int(HEART_WINDOW * 40))
        self.chest_rows: deque = deque(maxlen=int(BREATH_WINDOW * 40))
        self.chest = ChestMotion()
        self.last = 0.0
        self.estimated = 0.0
        self.nose: np.ndarray | None = None
        self.value: dict | None = None
        self.heart_seen: deque = deque(maxlen=AGREE)
        self.breath_seen: deque = deque(maxlen=AGREE)

    @staticmethod
    def _agreed(seen: deque, value: float, quality: float, minimum: float, spread: float) -> int | None:
        seen.append(float(value) if value and quality >= minimum else None)
        return pulse.agreed(list(seen), AGREE, spread)

    def sample(self, frame: np.ndarray, face, box, now: float) -> bool:
        if now - self.last < SAMPLE_GAP:
            return False
        self.last = now
        nose = np.array([float(face[8]), float(face[9])])
        if self.nose is not None and np.linalg.norm(nose - self.nose) > FACE_JUMP * max(1.0, float(box[2])):
            self.colors.clear()
            self.heart_seen.clear()
        self.nose = nose
        color = face_rgb(frame, face)
        if color is not None:
            self.colors.append((now, *color))
        position = self.chest.update(frame, box)
        if position is None:
            self.chest_rows.clear()
            self.breath_seen.clear()
        else:
            self.chest_rows.append((now, position))
        return True

    def estimate(self, now: float) -> dict | None:
        if now - self.estimated < ESTIMATE_EVERY:
            return self.value
        self.estimated = now
        colors = np.array([r for r in self.colors if now - r[0] <= HEART_WINDOW], dtype=np.float64).reshape(-1, 4)
        chest = np.array([r for r in self.chest_rows if now - r[0] <= BREATH_WINDOW], dtype=np.float64).reshape(-1, 2)
        bpm, heart_q = pulse.heart_rate(colors[:, 0], colors[:, 1:]) if len(colors) else (0.0, 0.0)
        rpm, breath_q = pulse.breath_rate(chest[:, 0], chest[:, 1]) if len(chest) else (0.0, 0.0)
        span = float(colors[-1, 0] - colors[0, 0]) if len(colors) > 1 else 0.0
        self.value = {"heart_rate": self._agreed(self.heart_seen, bpm, heart_q, HEART_MIN_QUALITY, HEART_SPREAD), "hr_quality": round(heart_q, 3),
                      "resp_rate": self._agreed(self.breath_seen, rpm, breath_q, BREATH_MIN_QUALITY, BREATH_SPREAD), "rr_quality": round(breath_q, 3),
                      "progress": round(min(1.0, span / HEART_WINDOW), 2), "at": round(now, 2)}
        return self.value


class VitalCam:

    def __init__(self) -> None:
        self.targets: dict[str, float] = {}
        self.meters: dict[int, PersonMeter] = {}
        self.cpu_ms = 0.0
        self.frames = 0
        self.lock = threading.Lock()

    def want(self, raw: str, now: float | None = None) -> None:
        now = now or time.time()
        slugs = [s for s in str(raw or "")[:600].split(",") if SLUG.match(s)][:MAX_TARGETS]
        with self.lock:
            self.targets = {s: t for s, t in self.targets.items() if t > now}
            for slug in slugs:
                self.targets[slug] = now + TARGET_TTL

    def active(self, now: float) -> set[str]:
        if not selection.rppg_enabled():
            return set()
        with self.lock:
            return {s for s, t in self.targets.items() if t > now}

    def busy(self, tracks: list, now: float) -> bool:
        wanted = self.active(now)
        return bool(wanted) and any(t.identity()[0] in wanted and now - t.last_seen <= TRACK_FRESH for t in tracks)

    def sample(self, frame: np.ndarray, tracks: list, now: float) -> None:
        wanted = self.active(now)
        alive = {t.id for t in tracks}
        self.meters = {k: m for k, m in self.meters.items() if k in alive}
        if not wanted:
            self.meters.clear()
            return
        started = time.process_time()
        for track in tracks:
            if track.identity()[0] not in wanted or track.face is None or not track.facing or now - track.last_seen > TRACK_FRESH:
                continue
            if self.meters.setdefault(track.id, PersonMeter()).sample(frame, track.face, track.box, now):
                self.frames += 1
        self.cpu_ms += (time.process_time() - started) * 1000

    def reading(self, track, now: float) -> dict | None:
        meter = self.meters.get(track.id)
        if meter is None or track.identity()[0] not in self.active(now):
            return None
        started = time.process_time()
        value = meter.estimate(now)
        self.cpu_ms += (time.process_time() - started) * 1000
        return value

    def cost(self) -> dict:
        return {"cpu_ms": round(self.cpu_ms, 1), "frames": self.frames}
