import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request

from appearance import classify

MAX_IMAGE = 3 * 1024 * 1024
MAX_BODIES = 24
MIN_SHARE = 0.4
STRIDE = 3
PEOPLE = {"persona": "person"}
VEHICLES = {"automobile": "car", "camion": "truck", "autobus": "truck", "moto": "motorbike", "bicicletta": "bicycle"}
ITEMS = {"zaino": "backpack", "borsa": "bag", "valigia": "suitcase", "ombrello": "umbrella", "cellulare": "phone"}
ANIMALS = {"cane", "gatto", "uccello", "cavallo"}
HI_VIS = {"yellow", "orange"}


def dominant(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> str | None:
    h, w = frame.shape[:2]
    x0, x1, y0, y1 = max(0, x0), min(w, x1), max(0, y0), min(h, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    region = np.ascontiguousarray(frame[y0:y1:STRIDE, x0:x1:STRIDE])
    names = classify(cv2.cvtColor(region, cv2.COLOR_BGR2HSV)).ravel()
    names = names[names != ""]
    if not names.size:
        return None
    values, counts = np.unique(names, return_counts=True)
    best = int(np.argmax(counts))
    return str(values[best]) if counts[best] / names.size >= MIN_SHARE else None


def bright(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> bool:
    region = frame[max(0, y0):max(0, y1):STRIDE, max(0, x0):max(0, x1):STRIDE]
    if not region.size:
        return False
    hsv = cv2.cvtColor(np.ascontiguousarray(region), cv2.COLOR_BGR2HSV)
    return float(np.mean((hsv[..., 1] > 150) & (hsv[..., 2] > 170))) > 0.35


def inside(item: list, box: list) -> bool:
    ix, iy, iw, ih = item
    x, y, w, h = box
    cx, cy = ix + iw / 2, iy + ih / 2
    return x - 0.25 * w <= cx <= x + 1.25 * w and y + 0.2 * h <= cy <= y + 1.05 * h


def person(frame: np.ndarray, box: list, carried: list) -> dict:
    x, y, w, h = box
    upper = dominant(frame, x + w // 5, y + int(h * 0.18), x + w - w // 5, y + int(h * 0.5))
    lower = dominant(frame, x + w // 5, y + int(h * 0.55), x + w - w // 5, y + int(h * 0.9))
    hi_vis = upper in HI_VIS and bright(frame, x + w // 5, y + int(h * 0.18), x + w - w // 5, y + int(h * 0.5))
    items = sorted({ITEMS[o["label"]] for o in carried if inside(o["box"], box)})
    return {"upper": upper, "lower": lower, "hi_vis": hi_vis, "carrying": items}


def describe(frame: np.ndarray, found: list) -> list:
    h, w = frame.shape[:2]
    carried = [o for o in found if o["label"] in ITEMS]
    out = []
    for o in sorted(found, key=lambda f: -f["score"]):
        label, box = o["label"], o["box"]
        norm = [round(min(1.0, max(0.0, v / s)), 4) for v, s in zip(box, (w, h, w, h))]
        row = {"box": norm, "score": float(o["score"])}
        if label in PEOPLE:
            out.append({**row, "class": "person", "look": person(frame, box, carried)})
        elif label in VEHICLES:
            x, y, bw, bh = box
            color = dominant(frame, x + bw // 5, y + bh // 5, x + bw - bw // 5, y + bh - bh // 5)
            out.append({**row, "class": "vehicle", "vehicle": {"kind": VEHICLES[label], "color": color}})
        elif label in ANIMALS:
            out.append({**row, "class": "animal"})
        if len(out) >= MAX_BODIES:
            break
    return out


def router(detector) -> APIRouter:
    api = APIRouter()

    @api.post("/bodies")
    async def bodies(request: Request):
        engine = detector()
        if engine is None:
            raise HTTPException(503, "vision_objects_unavailable")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_IMAGE:
                raise HTTPException(413, "vision_image_too_large")
        frame = cv2.imdecode(np.frombuffer(bytes(raw), np.uint8), cv2.IMREAD_COLOR) if raw else None
        if frame is None:
            raise HTTPException(400, "vision_image_invalid")
        return {"frame": [int(frame.shape[1]), int(frame.shape[0])], "bodies": describe(frame, engine.detect(frame))}

    return api
