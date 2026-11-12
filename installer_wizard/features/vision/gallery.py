import json
import logging
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1] / "biometrics"))
import embeddings as emb
import face_engine
import sealed_rows

log = logging.getLogger("nuxiva.vision")

FACES = Path(os.environ.get("NUXIVA_FACES_DIR", "/var/lib/nuxiva/faces"))
MATCH_THRESHOLD = float(os.environ.get("NUXIVA_FACE_THRESHOLD", "0.40"))
MARGIN = float(os.environ.get("NUXIVA_FACE_MARGIN", "0.05"))
TWIN_SIM = float(os.environ.get("NUXIVA_FACE_TWIN_SIM", "0.55"))
TWIN_MARGIN = float(os.environ.get("NUXIVA_FACE_TWIN_MARGIN", "0.12"))
IR_WEIGHT = float(os.environ.get("NUXIVA_FACE_IR_WEIGHT", "0.35"))
ADAPTIVE = os.environ.get("NUXIVA_FACE_ADAPTIVE", "1") != "0"
SHADOW_SIM = float(os.environ.get("NUXIVA_FACE_SHADOW_SIM", "0.62"))
MAX_SAMPLES = 40
MAX_MARKS = 24
UNKNOWN = "Sconosciuto"


def merge_rows(old: np.ndarray | None, new: np.ndarray) -> np.ndarray:
    return face_engine.merge(old, new, MAX_SAMPLES)


def save_marks(folder: Path, marks: list | None, meta: dict) -> None:
    fresh = [m for m in marks or [] if m is not None and np.asarray(m).size == face_engine.MARKS_DIM]
    if not fresh:
        return
    old = _load_rows(folder / "marks.npy", unit=False)
    rows = np.vstack([*(([old] if old is not None and old.shape[-1] == face_engine.MARKS_DIM else [])),
                      np.asarray(fresh, dtype=np.float32)])[-MAX_MARKS:]
    sealed_rows.save(folder / "marks.npy", rows)
    meta["marks_samples"] = len(rows)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "persona"


def _load_rows(path: Path, unit: bool = True) -> np.ndarray | None:
    try:
        rows = sealed_rows.load(path)
    except sealed_rows.SealedRowsError as exc:
        log.warning("Campioni volto illeggibili in %s: %s", path.parent.name, exc)
        return None
    except OSError:
        return None
    if rows is None:
        return None
    return emb.unit_rows(rows) if unit else np.asarray(rows, dtype=np.float32).reshape(len(rows), -1)


class Gallery:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.people: dict = {}
        self.twins: set = set()
        self.shadows: dict = {}
        self.engine = face_engine.build(face_engine.Settings(MATCH_THRESHOLD, MARGIN, TWIN_MARGIN, TWIN_SIM, IR_WEIGHT,
                                                             SHADOW_SIM, adaptive=ADAPTIVE))
        self.reload()

    def reload(self) -> None:
        people = {}
        FACES.mkdir(parents=True, exist_ok=True)
        for d in FACES.iterdir():
            try:
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            rows = _load_rows(d / "embeddings.npy")
            if rows is None:
                continue
            ir = _load_rows(d / "embeddings_ir.npy")
            marks = _load_rows(d / "marks.npy", unit=False)
            people[d.name] = {**meta, "slug": d.name, "embeddings": rows, "ir": ir, "marks": marks}
        self._finish(people)
        log.info("Galleria: %d persone registrate, %d coppie somiglianti, %d doppioni", len(people), len(self.twins),
                 len(self.shadows))

    def _finish(self, people: dict) -> None:
        with self.lock:
            self.engine.replace([(s, p["embeddings"], p["ir"], bool(p.get("auto")), p.get("marks"))
                                 for s, p in people.items()])
            report = {r["slug"]: r for r in self.engine.report()}
            for slug, p in people.items():
                r = report.get(slug, {})
                p["threshold"] = float(r.get("threshold", MATCH_THRESHOLD))
                p["threshold_ir"] = float(r.get("threshold_ir", MATCH_THRESHOLD))
                p["spread"] = r.get("spread")
                p["centroid"] = emb.centroid(p["embeddings"])
            self.people = people
            self.twins = {frozenset((a, b)) for a, b, _ in self.engine.twins()}
            self.shadows = {g: h for g, h, _ in self.engine.shadows()}

    def scores(self, feature: np.ndarray, ir_feature: np.ndarray | None = None) -> tuple[dict, dict | None]:
        with self.lock:
            return self.engine.scores(feature, ir_feature)

    def match_ex(self, feature: np.ndarray, ir_feature: np.ndarray | None = None, marks: np.ndarray | None = None) -> dict:
        with self.lock:
            result = self.engine.verdict(feature, ir_feature, marks)
            names = {s: p["name"] for s, p in self.people.items()}
        result["name"] = names.get(result["slug"], UNKNOWN)
        result["names"] = [names[s] for s in (result["best"], result["second"]) if s in names] if result["ambiguous"] else []
        return result

    def match(self, feature: np.ndarray, ir_feature: np.ndarray | None = None) -> tuple:
        r = self.match_ex(feature, ir_feature)
        if r["slug"]:
            return r["slug"], r["name"], r["score"]
        return None, UNKNOWN, r["score"]

    def closest(self, feature: np.ndarray) -> tuple[str | None, float]:
        with self.lock:
            return self.engine.closest(feature)

    def centroid_score(self, slug: str, feature: np.ndarray) -> float | None:
        with self.lock:
            return self.engine.centroid_score(slug, feature)

    def may_learn(self, slug: str, feature: np.ndarray, ir_feature: np.ndarray | None = None) -> bool:
        with self.lock:
            return self.engine.may_learn(slug, feature, ir_feature)

    def shadow_list(self) -> list[dict]:
        with self.lock:
            names = {s: p["name"] for s, p in self.people.items()}
            return [{"guest": g, "host": h, "guest_name": names.get(g, g), "host_name": names.get(h, h),
                     "similarity": round(float(sim), 3)} for g, h, sim in self.engine.shadows()]

    def next_guest_name(self) -> str:
        with self.lock:
            used = {p["name"] for p in self.people.values()}
        n = 1
        while f"Ospite {n}" in used:
            n += 1
        return f"Ospite {n}"

    def add_samples(self, slug: str, rgb: list, ir: list | None = None, marks: list | None = None) -> None:
        d = FACES / slug
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if len(rgb):
            merged = merge_rows(_load_rows(d / "embeddings.npy"), np.array(rgb))
            sealed_rows.save(d / "embeddings.npy", merged)
            meta["samples"] = len(merged)
        meta["updated"] = time.time()
        if ir:
            merged_ir = merge_rows(_load_rows(d / "embeddings_ir.npy"), np.array(ir))
            sealed_rows.save(d / "embeddings_ir.npy", merged_ir)
            meta["samples_ir"] = len(merged_ir)
        save_marks(d, marks, meta)
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.reload()

    def merge(self, source: str, target: str, name: str) -> dict:
        src, dst = FACES / slugify(source), FACES / slugify(target)
        if src == dst:
            raise ValueError("Un volto non può essere unito a se stesso")
        if not src.is_dir():
            raise FileNotFoundError(f"Volto {source} non trovato")
        dst.mkdir(parents=True, exist_ok=True)
        try:
            meta = json.loads((dst / "meta.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            meta = {"name": name, "enrolled_at": time.time(), "auto": False}
        for file, counter in (("embeddings.npy", "samples"), ("embeddings_ir.npy", "samples_ir")):
            incoming = _load_rows(src / file)
            if incoming is None:
                continue
            merged = emb.merge(_load_rows(dst / file), incoming, MAX_SAMPLES)
            sealed_rows.save(dst / file, merged)
            meta[counter] = len(merged)
        incoming_marks = _load_rows(src / "marks.npy", unit=False)
        if incoming_marks is not None:
            save_marks(dst, list(incoming_marks), meta)
        photos = dst / "photos"
        photos.mkdir(parents=True, exist_ok=True)
        if (src / "photo.jpg").is_file():
            shutil.copy2(src / "photo.jpg", photos / f"merged_{src.name}_{int(time.time())}.jpg")
            if not (dst / "photo.jpg").is_file():
                shutil.copy2(src / "photo.jpg", dst / "photo.jpg")
        for photo in (src / "photos").glob("*.jpg") if (src / "photos").is_dir() else ():
            shutil.copy2(photo, photos / f"merged_{src.name}_{photo.name}")
        meta.update(name=name, auto=False, updated=time.time(), merged_from=sorted({*meta.get("merged_from", []), src.name}))
        (dst / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        shutil.rmtree(src)
        self.reload()
        log.info("Volto %s unito a %s (%d campioni)", src.name, dst.name, meta.get("samples", 0))
        return {**meta, "slug": dst.name}

    def rename(self, slug: str, name: str) -> dict | None:
        d = FACES / slug
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        meta.update(name=name, auto=False, renamed_at=time.time())
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.reload()
        return {**meta, "slug": slug}

    def save(self, name: str, embeddings: list, photo: np.ndarray, auto: bool = False, slug: str | None = None,
             ir: list | None = None, marks: list | None = None) -> dict:
        slug = slug or slugify(name)
        d = FACES / slug
        d.mkdir(parents=True, exist_ok=True)
        merged = emb.merge(_load_rows(d / "embeddings.npy"), np.array(embeddings), MAX_SAMPLES)
        sealed_rows.save(d / "embeddings.npy", merged)
        meta = {"name": name, "enrolled_at": time.time(), "samples": len(merged), "auto": auto}
        if ir:
            merged_ir = emb.merge(_load_rows(d / "embeddings_ir.npy"), np.array(ir), MAX_SAMPLES)
            sealed_rows.save(d / "embeddings_ir.npy", merged_ir)
            meta["samples_ir"] = len(merged_ir)
        save_marks(d, marks, meta)
        photos_dir = d / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / "photo.jpg"), photo)
        cv2.imwrite(str(photos_dir / f"photo_{int(time.time())}.jpg"), photo)
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        os.chmod(d, 0o700)
        self.reload()
        return {**meta, "slug": slug}

    def delete(self, slug: str) -> bool:
        d = FACES / slug
        if not d.is_dir() or d.parent != FACES:
            return False
        shutil.rmtree(d)
        self.reload()
        return True

    def list_photos(self, slug: str) -> list[dict]:
        d = FACES / slugify(slug)
        if not d.is_dir():
            return []
        photos_dir = d / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        items = []
        primary_path = d / "photo.jpg"
        if primary_path.is_file():
            stat = primary_path.stat()
            items.append({
                "id": "photo_primary",
                "filename": "photo.jpg",
                "is_primary": True,
                "url": f"/api/vision/people/{slugify(slug)}/photo.jpg",
                "created_at": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
        for f in sorted(photos_dir.glob("*.jpg"), key=lambda p: -p.stat().st_mtime):
            stat = f.stat()
            items.append({
                "id": f.name,
                "filename": f.name,
                "is_primary": False,
                "url": f"/api/vision/people/{slugify(slug)}/photos/{f.name}",
                "created_at": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
        return items

    def delete_photo(self, slug: str, photo_id: str) -> bool:
        d = FACES / slugify(slug)
        if not d.is_dir():
            return False
        photos_dir = d / "photos"
        target = None
        if photo_id in ("photo_primary", "photo.jpg"):
            target = d / "photo.jpg"
        elif (photos_dir / photo_id).is_file():
            target = photos_dir / photo_id
        if not target or not target.is_file():
            return False
        try:
            target.unlink()
        except OSError:
            return False
        # If primary photo was deleted, promote another photo from photos_dir
        if target.name == "photo.jpg":
            remaining = sorted(photos_dir.glob("*.jpg"), key=lambda p: -p.stat().st_mtime)
            if remaining:
                shutil.copy(remaining[0], d / "photo.jpg")
        self.reproject_person(slug)
        return True

    def reproject_person(self, slug: str) -> dict:
        d = FACES / slugify(slug)
        if not d.is_dir():
            return {"ok": False, "error": "Directory non trovata"}
        emb_path = d / "embeddings.npy"
        rows = _load_rows(emb_path)
        if rows is None:
            return {"ok": False, "error": "Embeddings non trovati"}
        # Re-prune and clean embeddings against centroid
        cleaned = emb.prune(rows, MAX_SAMPLES)
        c = emb.centroid(cleaned)
        # Drop outliers that have similarity < 0.25 with centroid
        sims = cleaned @ c
        kept = cleaned[sims >= 0.25]
        if len(kept) < 2:
            kept = cleaned
        sealed_rows.save(emb_path, kept)
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {"name": slug, "enrolled_at": time.time()}
        meta["samples"] = len(kept)
        meta["reprojected_at"] = time.time()
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.reload()
        pct = quality_percent(len(kept), meta.get("samples_ir", 0), emb.intra_stats(kept))
        return {"ok": True, "samples": len(kept), "quality_pct": pct, "threshold": round(emb.person_threshold(kept, MATCH_THRESHOLD), 3)}

    def associate_face(self, from_slug: str, to_slug: str) -> dict:
        src = FACES / slugify(from_slug)
        dst = FACES / slugify(to_slug)
        if not src.is_dir() or not dst.is_dir():
            return {"ok": False, "error": "Cartelle volti non valide"}
        src_rows = _load_rows(src / "embeddings.npy")
        dst_rows = _load_rows(dst / "embeddings.npy")
        merged = emb.merge(dst_rows, src_rows if src_rows is not None else np.empty((0, 128), dtype=np.float32), MAX_SAMPLES)
        sealed_rows.save(dst / "embeddings.npy", merged)
        # Copy photos
        dst_photos = dst / "photos"
        dst_photos.mkdir(parents=True, exist_ok=True)
        if (src / "photo.jpg").is_file():
            shutil.copy(src / "photo.jpg", dst_photos / f"scan_{int(time.time())}.jpg")
        if (src / "photos").is_dir():
            for p in (src / "photos").glob("*.jpg"):
                shutil.copy(p, dst_photos / f"merged_{p.name}")
        shutil.rmtree(src, ignore_errors=True)
        self.reload()
        return self.reproject_person(to_slug)

    def listing(self) -> list:
        with self.lock:
            return [{k: v for k, v in p.items() if k not in ("embeddings", "ir", "centroid", "marks")} for p in self.people.values()]

    def health(self) -> list[dict]:
        with self.lock:
            people = dict(self.people)
            report = {r["slug"]: r for r in self.engine.report()}
        rows = []
        for slug, p in people.items():
            stats = emb.intra_stats(p["embeddings"])
            r = report.get(slug, {})
            similar = [{"slug": other, "name": people[other]["name"], "similarity": round(float(sim), 3)}
                       for other, sim in r.get("similar", []) if other in people]
            samples, ir = len(p["embeddings"]), 0 if p["ir"] is None else len(p["ir"])
            q_label = quality(samples, ir, stats, bool(similar))
            q_pct = quality_percent(samples, ir, stats, bool(similar))
            rows.append({"slug": slug, "name": p["name"], "samples": samples, "samples_ir": ir,
                         "threshold": round(p["threshold"], 3), "threshold_ir": round(p["threshold_ir"], 3),
                         "spread": round(stats[1], 3) if stats else None, "similar": similar,
                         "shadow_of": r.get("shadow_of"), "marks": r.get("marks", []),
                         "marks_samples": r.get("marks_samples", 0), "quality": q_label, "quality_pct": q_pct})
        return sorted(rows, key=lambda r: r["name"].lower())


def quality_percent(samples: int, ir: int = 0, stats: tuple | None = None, has_twin: bool = False) -> int:
    if samples <= 0:
        return 0
    base = min(88, 30 + int(samples * 2.2))
    if stats and len(stats) >= 2 and stats[1] is not None:
        spread = stats[1]
        if spread < 0.10:
            base += 8
        elif spread < 0.15:
            base += 4
        elif spread > 0.25:
            base -= 10
    if ir > 0:
        base += min(6, ir * 2)
    if has_twin:
        base -= 10
    return max(15, min(99, base))


def quality(samples: int, ir: int, stats: tuple | None, has_twin: bool) -> str:
    if samples < 6:
        return "da migliorare"
    if has_twin and (ir < 8 or samples < 20):
        return "da migliorare"
    if samples >= 15 and (stats is None or stats[1] < 0.12):
        return "ottima"
    return "buona"
