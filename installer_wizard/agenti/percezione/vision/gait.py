import json
import math
from backend import native_core

AREA = "gait"
GAIT_DIM = 16
SIMILARITY_THRESHOLD = 0.70
MIN_CONFIDENCE_THRESHOLD = 0.40


def _engine_class():
    return native_core.symbol("RustGaitCore")


class GaitCore:

    def __init__(self, prefer_native: bool = True) -> None:
        self.prefer_native = prefer_native
        self._engine = None

    def ready(self):
        if self._engine is None and self.prefer_native:
            cls = _engine_class()
            if cls is not None:
                self._engine = cls()
        return self._engine

    def extract(self, observations: list[dict]) -> dict:
        engine = self.ready()
        if engine is not None:
            raw = engine.extract(json.dumps(observations))
            return json.loads(raw)
        return self._py_extract(observations)

    def evaluate(self, candidate: dict, reference: dict, ref_id: str | None = None,
                 ref_ts_ms: int | None = None) -> dict:
        engine = self.ready()
        if engine is not None:
            cand_raw = json.dumps(candidate)
            ref_raw = json.dumps(reference)
            raw = engine.evaluate(cand_raw, ref_raw, ref_id, ref_ts_ms)
            return json.loads(raw)
        return self._py_evaluate(candidate, reference, ref_id, ref_ts_ms)

    def find_best(self, candidate: dict, references: list[dict]) -> dict | None:
        engine = self.ready()
        if engine is not None:
            cand_raw = json.dumps(candidate)
            refs_raw = json.dumps(references)
            raw = engine.find_best(cand_raw, refs_raw)
            return json.loads(raw)
        return self._py_find_best(candidate, references)

    def aggregate(self, signatures: list[dict]) -> dict:
        engine = self.ready()
        if engine is not None:
            raw = engine.aggregate(json.dumps(signatures))
            return json.loads(raw)
        return self._py_aggregate(signatures)

    def _py_extract(self, observations: list[dict]) -> dict:
        if len(observations) < 5:
            raise ValueError("gait: insufficient samples")
        sorted_obs = sorted(observations, key=lambda o: o["timestamp_ms"])
        first_t = sorted_obs[0]["timestamp_ms"]
        last_t = sorted_obs[-1]["timestamp_ms"]
        dur_ms = last_t - first_t
        if dur_ms < 400:
            raise ValueError("gait: observation duration too short")
        for o in sorted_obs:
            if o.get("width", 0) <= 0 or o.get("height", 0) <= 0:
                raise ValueError("gait: invalid bounding box coordinates")
        dur_s = max(0.1, dur_ms / 1000.0)
        heights = [float(o["height"]) for o in sorted_obs]
        widths = [float(o["width"]) for o in sorted_obs]
        centers_y = [float(o["y"]) + float(o["height"]) * 0.5 for o in sorted_obs]
        centers_x = [float(o["x"]) + float(o["width"]) * 0.5 for o in sorted_obs]
        ars = [float(o["width"]) / float(o["height"]) for o in sorted_obs]
        mean_h = max(1.0, sum(heights) / len(heights))
        mean_w = max(1.0, sum(widths) / len(widths))
        mean_ar = sum(ars) / len(ars)
        var_ar = sum((a - mean_ar) ** 2 for a in ars) / max(1, len(ars))
        dx = centers_x[-1] - centers_x[0]
        dy = centers_y[-1] - centers_y[0]
        dist = math.sqrt(dx * dx + dy * dy)
        speed = min(5.0, (dist / mean_h) / dur_s)
        norm_cadence = 0.83
        rel_stride = min(2.0, (dist / max(1.0, dur_s * 1.6)) / mean_h)
        vert_osc = min(1.0, (max(centers_y) - min(centers_y)) / mean_h)
        lat_sway = min(1.0, (max(centers_x) - min(centers_x)) / mean_w)
        symmetry = 0.8
        features = [
            norm_cadence, rel_stride, vert_osc, lat_sway, symmetry,
            min(2.0, mean_ar), min(1.0, var_ar), speed,
            0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1
        ]
        return {"features": features, "samples": len(sorted_obs), "confidence": 0.6}

    def _py_evaluate(self, candidate: dict, reference: dict, ref_id: str | None = None,
                     ref_ts_ms: int | None = None) -> dict:
        c_feats = candidate.get("features", [])
        r_feats = reference.get("features", [])
        if len(c_feats) != GAIT_DIM or len(r_feats) != GAIT_DIM:
            raise ValueError("gait: signature must have 16 dimensions")
        dot = sum(a * b for a, b in zip(c_feats, r_feats))
        norm_a = math.sqrt(sum(a * a for a in c_feats))
        norm_b = math.sqrt(sum(b * b for b in r_feats))
        sim = max(0.0, min(1.0, dot / (norm_a * norm_b))) if norm_a > 1e-6 and norm_b > 1e-6 else 0.0
        c_conf = candidate.get("confidence", 0.5)
        r_conf = reference.get("confidence", 0.5)
        conf = max(0.0, min(1.0, math.sqrt(c_conf * r_conf) * sim))
        prob = sim >= SIMILARITY_THRESHOLD and conf >= MIN_CONFIDENCE_THRESHOLD
        conf_pct = int(round(conf * 100.0))
        return {
            "similarity": sim,
            "confidence": conf,
            "probable_match": prob,
            "is_biometric_conclusive": False,
            "reference_id": ref_id,
            "reference_timestamp_ms": ref_ts_ms,
            "narrative_it": f"probabilmente la stessa persona, confidenza {conf_pct}%" if prob else f"andatura non corrispondente, similarità {conf_pct}%",
            "narrative_en": f"likely the same person, confidence {conf_pct}%" if prob else f"gait does not match, similarity {conf_pct}%",
            "narrative_fr": f"probablement la même personne, confiance {conf_pct}%" if prob else f"démarche non correspondante, similarité {conf_pct}%",
            "narrative_es": f"probablemente la misma persona, confianza {conf_pct}%" if prob else f"marcha no coincidente, similitud {conf_pct}%",
        }

    def _py_find_best(self, candidate: dict, references: list[dict]) -> dict | None:
        if not references:
            return None
        best = None
        for r in references:
            m = self._py_evaluate(candidate, r.get("signature", {}), r.get("id"), r.get("timestamp_ms"))
            if best is None or m["similarity"] > best["similarity"]:
                best = m
        return best

    def _py_aggregate(self, signatures: list[dict]) -> dict:
        if not signatures:
            raise ValueError("gait: insufficient samples")
        n = len(signatures)
        sum_f = [0.0] * GAIT_DIM
        total_samples = sum(s.get("samples", 0) for s in signatures)
        total_conf = sum(s.get("confidence", 0.0) for s in signatures)
        for s in signatures:
            feats = s.get("features", [])
            for i in range(GAIT_DIM):
                sum_f[i] += feats[i]
        return {
            "features": [v / n for v in sum_f],
            "samples": total_samples,
            "confidence": min(1.0, total_conf / n),
        }


gait_engine = GaitCore()
