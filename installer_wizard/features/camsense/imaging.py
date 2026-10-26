import cv2
import numpy as np

from features.camsense.model import SenseError

SIDE = 32
BINS = (8, 4, 4)
GRID = 12
MAX_PIXELS = 40_000_000


def decode(jpeg: bytes) -> np.ndarray:
    if not jpeg or len(jpeg) > 20_000_000:
        raise SenseError("frame_unavailable", 502)
    image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.shape[0] * image.shape[1] > MAX_PIXELS:
        raise SenseError("frame_invalid", 502)
    return image


def bounds(image: np.ndarray, area: list[float]) -> tuple[int, int, int, int]:
    height, width = image.shape[:2]
    x0, y0 = int(area[0] * width), int(area[1] * height)
    x1, y1 = max(x0 + 2, int((area[0] + area[2]) * width)), max(y0 + 2, int((area[1] + area[3]) * height))
    return x0, y0, min(x1, width), min(y1, height)


def unit(values: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(values))
    return values / norm if norm > 1e-9 else values


def vector(jpeg: bytes, area: list[float]) -> list[float]:
    image = decode(jpeg)
    x0, y0, x1, y1 = bounds(image, area)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        raise SenseError("invalid_region")
    small = cv2.resize(crop, (SIDE, SIDE), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    colour = cv2.calcHist([hsv], [0, 1, 2], None, list(BINS), [0, 180, 0, 256, 0, 256]).flatten()
    grid = cv2.resize(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (GRID, GRID), interpolation=cv2.INTER_AREA).astype(np.float64).flatten()
    shape = (grid - grid.mean()) / (grid.std() + 1e-6)
    merged = np.concatenate([unit(colour), unit(shape)]) / np.sqrt(2)
    return [round(float(v), 4) for v in merged]


def outline(jpeg: bytes, area: list[float]) -> bytes:
    image = decode(jpeg)
    x0, y0, x1, y1 = bounds(image, area)
    cv2.rectangle(image, (x0, y0), (x1 - 1, y1 - 1), (0, 220, 255), 3)
    ok, data = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise SenseError("frame_invalid", 502)
    return data.tobytes()
