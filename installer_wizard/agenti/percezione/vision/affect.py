import math
from collections import deque

import cv2
import numpy as np

MEASURE_EVERY = 0.4
WINDOW = 24
MIN_FRAMES = 6
GLABELLA_SIZE = (32, 20)


def _point(face, index: int) -> np.ndarray:
    return np.array([float(face[index]), float(face[index + 1])])


def landmarks(face) -> tuple[np.ndarray, ...]:
    return tuple(_point(face, 4 + 2 * i) for i in range(5))


def mouth_geometry(face) -> dict | None:
    right_eye, left_eye, nose, right_mouth, left_mouth = landmarks(face)
    ioc = float(np.linalg.norm(left_eye - right_eye))
    if ioc < 12:
        return None
    mouth_mid = (right_mouth + left_mouth) / 2
    eye_axis = math.atan2(*(left_eye - right_eye)[::-1])
    mouth_axis = math.atan2(*(left_mouth - right_mouth)[::-1])
    return {"width": float(np.linalg.norm(left_mouth - right_mouth)) / ioc,
            "drop": float(mouth_mid[1] - nose[1]) / ioc,
            "tilt": mouth_axis - eye_axis}


def glabella_energy(gray: np.ndarray, face) -> float | None:
    right_eye, left_eye, _, _, _ = landmarks(face)
    ioc = float(np.linalg.norm(left_eye - right_eye))
    center = (right_eye + left_eye) / 2 - np.array([0.0, 0.32 * ioc])
    half_w, half_h = 0.26 * ioc, 0.17 * ioc
    x0, x1 = int(center[0] - half_w), int(center[0] + half_w)
    y0, y1 = int(center[1] - half_h), int(center[1] + half_h)
    height, width = gray.shape[:2]
    if x0 < 0 or y0 < 0 or x1 >= width or y1 >= height or x1 - x0 < 6 or y1 - y0 < 4:
        return None
    patch = cv2.resize(gray[y0:y1, x0:x1], GLABELLA_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)
    gradient = np.abs(cv2.Sobel(patch, cv2.CV_32F, 1, 0, ksize=3))
    return float(gradient.mean() / (patch.mean() + 8.0))


def pose_vector(face) -> np.ndarray:
    right_eye, left_eye, nose, right_mouth, left_mouth = landmarks(face)
    ioc = max(1.0, float(np.linalg.norm(left_eye - right_eye)))
    origin = (right_eye + left_eye) / 2
    return np.concatenate([(p - origin) / ioc for p in (nose, right_mouth, left_mouth)])


class AffectMeter:

    def __init__(self) -> None:
        self.poses: deque = deque(maxlen=WINDOW)
        self.last = 0.0
        self.value: dict | None = None

    def update(self, frame: np.ndarray, face, now: float) -> dict | None:
        if now - self.last < MEASURE_EVERY:
            return self.value
        self.last = now
        mouth = mouth_geometry(face)
        gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brow = glabella_energy(gray, face) if mouth else None
        if mouth is None or brow is None:
            self.value = None
            return None
        self.poses.append(pose_vector(face))
        mimic = float(np.std(np.stack(self.poses), axis=0).mean()) if len(self.poses) >= MIN_FRAMES else None
        self.value = {"width": round(mouth["width"], 4), "drop": round(mouth["drop"], 4), "tilt": round(mouth["tilt"], 4),
                      "brow": round(brow, 4), "mimic": None if mimic is None else round(mimic, 5), "at": round(now, 2)}
        return self.value
