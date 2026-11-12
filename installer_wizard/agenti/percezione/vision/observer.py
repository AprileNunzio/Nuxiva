import asyncio
import logging
import os
import re
import threading
import time

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Request

from views import MAX_BYTES, decode

log = logging.getLogger("nuxiva.vision.observer")

ENABLED = os.environ.get("NUXIVA_OBSERVE_CAMERAS", "1") != "0"
MIN_FACE = int(os.environ.get("NUXIVA_OBSERVE_MIN_FACE", "56"))
MIN_SHARPNESS = 35.0
CLUSTER_SIMILARITY = 0.50
MERGE_THRESHOLD = 0.30
SAMPLES_TO_ENROLL = 5
PENDING_TTL = 600.0
MAX_PENDING = 32
SOURCE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n else v


class Observer:
    def __init__(self, views, gallery) -> None:
        self.views, self.gallery = views, gallery
        self.pending: dict[str, list[dict]] = {}
        self.lock = threading.Lock()

    def _faces(self, img: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
        h, w = img.shape[:2]
        out = []
        with self.views.lock:
            self.views.detector.setInputSize((w, h))
            _, faces = self.views.detector.detect(img)
            for face in [] if faces is None else faces:
                if float(face[2]) < MIN_FACE:
                    continue
                out.append((face, self.views.recognizer.feature(self.views.recognizer.alignCrop(img, face)).flatten()))
        return out

    def _sharp(self, crop: np.ndarray) -> bool:
        return crop.size > 0 and cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() >= MIN_SHARPNESS

    def _expire(self, now: float) -> None:
        for source in list(self.pending):
            alive = [c for c in self.pending[source] if now - c["at"] < PENDING_TTL]
            if alive:
                self.pending[source] = alive[-MAX_PENDING:]
            else:
                del self.pending[source]

    def _cluster(self, source: str, feature: np.ndarray, crop: np.ndarray, now: float) -> dict:
        clusters = self.pending.setdefault(source, [])
        unit = _unit(feature)
        best = max(clusters, key=lambda c: float(c["centroid"] @ unit), default=None)
        if best is None or float(best["centroid"] @ unit) < CLUSTER_SIMILARITY:
            best = {"features": [], "centroid": unit, "crop": crop, "at": now}
            clusters.append(best)
        best["features"].append(feature)
        best["centroid"] = _unit(np.mean([_unit(f) for f in best["features"]], axis=0))
        best["at"] = now
        if crop.shape[0] * crop.shape[1] > best["crop"].shape[0] * best["crop"].shape[1]:
            best["crop"] = crop
        return best

    def _adopt(self, source: str, cluster: dict, now: float) -> str:
        self.pending[source] = [c for c in self.pending.get(source, []) if c is not cluster]
        near_slug, near_score = self.gallery.closest(cluster["centroid"])
        if near_slug and near_score >= MERGE_THRESHOLD:
            self.gallery.add_samples(near_slug, cluster["features"])
            return near_slug
        person = self.gallery.save(self.gallery.next_guest_name(), cluster["features"], cluster["crop"], auto=True,
                                   slug=f"ospite-{int(now * 1000)}")
        log.info("Nuova persona vista dalla telecamera %s: %s", source, person["name"])
        return person["slug"]

    def observe(self, source: str, img: np.ndarray) -> dict:
        now = time.time()
        known, created, pending = [], [], 0
        faces = self._faces(img)
        with self.lock:
            self._expire(now)
            for face, feature in faces:
                crop = self.views.vision._crop(img, tuple(int(v) for v in face[:4]))
                r = self.gallery.match_ex(feature)
                if r["slug"]:
                    known.append(r["slug"])
                    self.views.auto(r["slug"], img, face)
                    if self.gallery.may_learn(r["slug"], feature):
                        self.gallery.add_samples(r["slug"], [feature])
                    continue
                if r.get("ambiguous") or not self._sharp(crop):
                    continue
                cluster = self._cluster(source, feature, crop, now)
                if len(cluster["features"]) >= SAMPLES_TO_ENROLL:
                    created.append(self._adopt(source, cluster, now))
                else:
                    pending += 1
        return {"source": source, "faces": len(faces), "known": sorted(set(known)), "created": created, "pending": pending}


def router(observer: Observer) -> APIRouter:
    r = APIRouter()

    @r.post("/observe")
    async def observe(request: Request):
        if not ENABLED:
            return {"enabled": False}
        source = str(request.query_params.get("source", ""))
        if not SOURCE_RE.match(source):
            raise HTTPException(400, "Sorgente non valida")
        data = await request.body()
        if not data or len(data) > MAX_BYTES:
            raise HTTPException(413, "Fotogramma vuoto o troppo grande")
        try:
            img = decode(data)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        return await asyncio.to_thread(observer.observe, source, img)

    return r
