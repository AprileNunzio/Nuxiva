import itertools
import logging
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter, Query

ROOT = str(Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from features.rescue.posture import PyPosture

log = logging.getLogger("nuxiva.vision.posture")

REST = {"letto", "divano"}
KEEP = 64
MAX_BODIES = 32
CAMERA = "vision:main"


def native_posture():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPosture", None)


def _overlap(a: list, b: list) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    iw = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    ih = max(0, min(ay + ah, by + bh) - max(ay, by))
    return iw * ih / max(1, aw * ah)


def bodies_of(found: list) -> list[tuple]:
    rest = [o["box"] for o in found if o.get("label") in REST]
    out = []
    for o in found:
        if o.get("label") != "persona":
            continue
        x, y, w, h = (float(v) for v in o["box"])
        on_rest = any(_overlap(o["box"], r) >= 0.35 for r in rest)
        out.append((x, y, w, h, float(o.get("score", 0.0)), on_rest))
    return out[:MAX_BODIES]


class PostureWatch:
    def __init__(self, prefer_native: bool = True) -> None:
        cls = native_posture() if prefer_native else None
        if cls is None and prefer_native:
            log.warning("Caduta e immobilità: uso il motore Python perché il modulo Rust non è disponibile")
        self.engine = cls() if cls is not None else PyPosture()
        self.events: deque = deque(maxlen=KEEP)
        self.seq = itertools.count(1)
        self.lock = threading.Lock()
        self.last = 0

    @property
    def native(self) -> bool:
        return not isinstance(self.engine, PyPosture)

    def observe(self, found: list, width: int, height: int, now: float | None = None, camera: str = CAMERA) -> list:
        moment = time.time() if now is None else now
        events = self.engine.observe(camera, moment, float(width), float(height), bodies_of(found))
        rows = [{"seq": 0, "camera": c, "track": tr, "kind": k, "probability": round(p, 4), "confidence": round(cf, 4),
                 "at": at} for c, tr, k, p, cf, at in events]
        with self.lock:
            for row in rows:
                row["seq"] = self.last = next(self.seq)
                self.events.append(row)
        return rows

    def since(self, seq: int) -> list:
        with self.lock:
            return [e for e in self.events if e["seq"] > seq]


def router(watch: PostureWatch) -> APIRouter:
    api = APIRouter()

    @api.get("/posture")
    async def posture(since: int = Query(0, ge=0, le=2**53)):
        return {"events": watch.since(since), "last": watch.last, "native": watch.native}

    return api
