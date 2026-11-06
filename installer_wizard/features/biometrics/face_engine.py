import logging
import os

import numpy as np

import embeddings as emb

log = logging.getLogger("nuxiva.vision")
DEFAULT_DIM = 128
_warned: set[str] = set()


def native_class():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustFaceBook", None)


def _fallback(area: str) -> None:
    if area not in _warned:
        _warned.add(area)
        log.warning("Sezione %s: uso il motore Python deprecato perché il modulo Rust non è disponibile", area)


def blob(rows) -> bytes:
    return np.ascontiguousarray(emb.unit_rows(rows), dtype="<f4").tobytes()


def empty_verdict() -> dict:
    return {"slug": None, "best": None, "score": 0.0, "second": None, "second_score": 0.0, "ambiguous": False,
            "twin": False, "reason": "nessuno"}


class Settings:
    def __init__(self, base: float = 0.40, margin: float = 0.05, twin_margin: float = 0.12, twin_sim: float = 0.55,
                 ir_weight: float = 0.35, shadow_sim: float = 0.62, learn_margin: float = 0.08,
                 adaptive: bool = True) -> None:
        self.base, self.margin, self.twin_margin, self.twin_sim = base, margin, twin_margin, twin_sim
        self.ir_weight, self.shadow_sim, self.learn_margin, self.adaptive = ir_weight, shadow_sim, learn_margin, adaptive

    def as_kwargs(self) -> dict:
        return {"base": self.base, "margin": self.margin, "twin_margin": self.twin_margin, "twin_sim": self.twin_sim,
                "ir_weight": self.ir_weight, "shadow_sim": self.shadow_sim, "learn_margin": self.learn_margin,
                "adaptive": self.adaptive}


class PyFaceBook:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.people: dict = {}
        self.twin_set: set = set()
        self.shadow_map: dict = {}
        self.similarity: dict = {}

    def replace(self, entries: list) -> int:
        s = self.s
        people = {}
        for slug, rows, ir, auto in entries:
            if rows is None or not len(rows):
                continue
            rows = emb.unit_rows(rows)
            ir = None if ir is None or not len(ir) else emb.unit_rows(ir)
            people[slug] = {"embeddings": rows, "ir": ir, "auto": bool(auto), "centroid": emb.centroid(rows),
                            "threshold": emb.person_threshold(rows, s.base) if s.adaptive else s.base,
                            "threshold_ir": emb.person_threshold(ir, s.base) if s.adaptive and ir is not None else s.base,
                            "spread": emb.genuine_spread(rows)}
        self.similarity = emb.centroid_similarities({k: p["centroid"] for k, p in people.items()})
        self.twin_set = {k for k, v in self.similarity.items() if v >= s.twin_sim}
        self.shadow_map = emb.shadow_pairs(people, self.similarity, s.shadow_sim)
        self.people = people
        return len(people)

    def scores(self, feature, ir=None):
        rgb = {k: emb.score_against(p["embeddings"], feature) for k, p in self.people.items()}
        irs = {k: emb.score_against(p["ir"], ir) for k, p in self.people.items() if p["ir"] is not None} if ir is not None else None
        return rgb, irs or None

    def verdict(self, feature, ir=None) -> dict:
        if not self.people:
            return empty_verdict()
        rgb, irs = self.scores(feature, ir)
        fused, conflict = emb.fuse(rgb, irs, self.s.ir_weight, self.s.base)
        limits = {k: p["threshold"] for k, p in self.people.items()}
        return emb.decide(fused, limits, self.s.base, self.s.margin, self.s.twin_margin, self.twin_set, conflict,
                          self.shadow_map)

    def closest(self, feature):
        best = (None, 0.0)
        for slug, p in self.people.items():
            score = emb.score_against(p["embeddings"], feature)
            if score > best[1]:
                best = (slug, score)
        return best

    def centroid_score(self, slug: str, feature):
        p = self.people.get(slug)
        return None if p is None else float(p["centroid"] @ emb.unit(np.asarray(feature, dtype=np.float32)))

    def may_learn(self, slug: str, feature, ir=None) -> bool:
        v = self.verdict(feature, ir)
        if v["slug"] != slug:
            return False
        if v["twin"] and self.shadow_map.get(v["second"] or "") != slug:
            return v["score"] - v["second_score"] >= self.s.twin_margin
        return v["score"] >= self.people.get(slug, {}).get("threshold", self.s.base) + self.s.learn_margin

    def shadows(self) -> list:
        return [(g, h, self.similarity.get(frozenset((g, h)), 0.0)) for g, h in sorted(self.shadow_map.items())]

    def twins(self) -> list:
        return [(*sorted(pair), self.similarity[pair]) for pair in sorted(self.twin_set, key=sorted)]

    def report(self) -> list:
        rows = []
        for slug, p in sorted(self.people.items()):
            similar = [(next(iter(pair - {slug})), self.similarity[pair]) for pair in self.twin_set if slug in pair]
            rows.append({"slug": slug, "threshold": p["threshold"], "threshold_ir": p["threshold_ir"],
                         "spread": p["spread"], "similar": sorted(similar), "shadow_of": self.shadow_map.get(slug)})
        return rows


class NativeFaceBook:
    def __init__(self, cls, settings: Settings) -> None:
        self.cls, self.s = cls, settings
        self.book = cls(dim=DEFAULT_DIM, **settings.as_kwargs())
        self.dim = DEFAULT_DIM
        self.count = 0

    def replace(self, entries: list) -> int:
        rows = [(slug, r, ir, auto) for slug, r, ir, auto in entries if r is not None and len(r)]
        dims = {np.asarray(r).reshape(len(r), -1).shape[1] for _, r, _, _ in rows}
        dim = dims.pop() if len(dims) == 1 else DEFAULT_DIM
        if dims:
            raise ValueError("face.rows.dimension")
        if dim != self.dim:
            self.book, self.dim = self.cls(dim=dim, **self.s.as_kwargs()), dim
        self.count = self.book.replace([(slug, blob(r), None if ir is None or not len(ir) else blob(ir), bool(auto))
                                        for slug, r, ir, auto in rows])
        return self.count

    def _probe(self, feature) -> bytes | None:
        v = np.asarray(feature, dtype=np.float32).reshape(-1)
        return blob(v) if self.count and v.size == self.dim else None

    def scores(self, feature, ir=None):
        probe = self._probe(feature)
        if probe is None:
            return {}, None
        rgb, irs = self.book.scores(probe, self._probe(ir) if ir is not None else None)
        return dict(rgb), (dict(irs) if irs else None)

    def verdict(self, feature, ir=None) -> dict:
        probe = self._probe(feature)
        if probe is None:
            return empty_verdict()
        return dict(self.book.verdict(probe, self._probe(ir) if ir is not None else None))

    def closest(self, feature):
        probe = self._probe(feature)
        return (None, 0.0) if probe is None else tuple(self.book.closest(probe))

    def centroid_score(self, slug: str, feature):
        probe = self._probe(feature)
        return None if probe is None else self.book.centroid_score(slug, probe)

    def may_learn(self, slug: str, feature, ir=None) -> bool:
        probe = self._probe(feature)
        return False if probe is None else bool(self.book.may_learn(slug, probe, self._probe(ir) if ir is not None else None))

    def shadows(self) -> list:
        return [tuple(r) for r in self.book.shadows()]

    def twins(self) -> list:
        return [tuple(r) for r in self.book.twins()]

    def report(self) -> list:
        return [dict(r) for r in self.book.report()]


def build(settings: Settings):
    cls = native_class()
    if cls is None:
        _fallback("riconoscimento del volto")
        return PyFaceBook(settings)
    return NativeFaceBook(cls, settings)


def merge(old, new, limit: int) -> np.ndarray:
    fresh = emb.unit_rows(new)
    cls = native_class()
    if cls is None or not len(fresh):
        return emb.merge(old, fresh, limit)
    import nuxiva_native
    dim = fresh.shape[1]
    previous = None if old is None or not len(old) else blob(old)
    raw = nuxiva_native.face_merge_rows(previous, blob(fresh), dim, limit)
    return np.frombuffer(raw, dtype="<f4").reshape(-1, dim).copy()
