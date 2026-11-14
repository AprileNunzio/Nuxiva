import base64
import json
import logging
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import cv2
import numpy as np

log = logging.getLogger("nuxiva.vision.capture")

THUMB_W = 9
THUMB_H = 8
TILE = 16
HIST_BINS = (6, 3, 3)
MAX_REPLY = 1_048_576
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def thumb(image: np.ndarray) -> bytes:
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA).astype(np.uint8).tobytes()


def tile_embedding(image: np.ndarray) -> list[float]:
    small = cv2.resize(image, (TILE, TILE), interpolation=cv2.INTER_AREA)
    if small.ndim == 2:
        small = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32).flatten()
    gray -= float(gray.mean())
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, list(HIST_BINS), [0, 180, 0, 256, 0, 256]).flatten()
    hist /= max(float(hist.sum()), 1.0)
    vector = np.concatenate([gray / 255.0, hist * 4.0]).astype(np.float32)
    return [float(x) for x in vector]


class TileEmbedder:
    name = "tile"

    def embed(self, image: np.ndarray) -> list[float] | None:
        return tile_embedding(image)


def _local(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "http" and (parts.hostname or "") in LOOPBACK


class VlmEmbedder:
    name = "vlm"

    def __init__(self, base_url: str, vision_model: str, embed_model: str, timeout: float = 30.0) -> None:
        if not _local(base_url):
            raise ValueError("vision.capture.vlm_not_local")
        if not vision_model or not embed_model:
            raise ValueError("vision.capture.vlm_model")
        self.base_url = base_url.rstrip("/")
        self.vision_model = vision_model
        self.embed_model = embed_model
        self.timeout = timeout

    def _post(self, path: str, body: dict) -> dict:
        request = urllib.request.Request(self.base_url + path, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                raw = reply.read(MAX_REPLY + 1)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            log.warning("Modello visivo locale non raggiungibile: %s", exc)
            return {}
        if len(raw) > MAX_REPLY:
            return {}
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def embed(self, image: np.ndarray) -> list[float] | None:
        ok, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            return None
        caption = self._post("/api/generate", {"model": self.vision_model, "stream": False,
                                               "prompt": "Describe in one short sentence what is on screen or in the room.",
                                               "images": [base64.b64encode(jpeg.tobytes()).decode()]})
        text = str(caption.get("response") or "").strip()[:600]
        if not text:
            return None
        vectors = self._post("/api/embed", {"model": self.embed_model, "input": [text]}).get("embeddings")
        if not isinstance(vectors, list) or not vectors or not isinstance(vectors[0], list):
            return None
        try:
            return [float(x) for x in vectors[0]]
        except (TypeError, ValueError):
            return None
