import math
import re

MAX_CAMERAS = 16
MAX_TRACKS = 16
MAX_BODIES = 32
MAX_SAMPLES = 96
UPRIGHT = 1.4
LOW_ASPECT = 1.0
LOW_SHRINK = 0.4
MIN_DROP = 0.35
MATCH_IOU = 0.15
HISTORY_S = 30.0
LABEL = re.compile(r"^[A-Za-z0-9_.:/-]{1,96}$")
DEFAULTS = {"fall_window_s": 2.5, "confirm_s": 4.0, "immobile_s": 60.0, "still_frac": 0.04, "max_gap_s": 6.0}
LIMITS = {"fall_window_s": (0.5, 6.0), "confirm_s": (1.0, 30.0), "immobile_s": (10.0, 3600.0),
          "still_frac": (0.005, 0.3), "max_gap_s": (1.0, 60.0)}


def _finite(*values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def _iou(a: dict, b: dict) -> float:
    ax0, ax1, ay0, ay1 = a["cx"] - a["w"] / 2.0, a["cx"] + a["w"] / 2.0, a["top"], a["top"] + a["h"]
    bx0, bx1, by0, by1 = b["cx"] - b["w"] / 2.0, b["cx"] + b["w"] / 2.0, b["top"], b["top"] + b["h"]
    inter = max(min(ax1, bx1) - max(ax0, bx0), 0.0) * max(min(ay1, by1) - max(ay0, by0), 0.0)
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0.0 else 0.0


def _sample(body, fw: float, fh: float, t: float) -> dict | None:
    x, y, w, h, score, rest = body
    if not _finite(x, y, w, h, score) or w <= 1.0 or h <= 1.0 or x < -fw or y < -fh or x > fw * 2.0 or y > fh * 2.0:
        return None
    return {"t": t, "cx": (x + w / 2.0) / fh, "cy": (y + h / 2.0) / fh, "top": y / fh, "w": w / fh, "h": h / fh,
            "aspect": h / w, "score": min(1.0, max(0.0, score)), "rest": bool(rest)}


class Track:
    def __init__(self, ident: int) -> None:
        self.id = ident
        self.samples: list[dict] = []
        self.candidate: tuple | None = None
        self.fell = False
        self.fall_sent = False
        self.anchor: dict | None = None
        self.immobile_sent = False

    def upright_ref(self, now: float, window: float) -> dict | None:
        for s in reversed(self.samples[:-1]):
            if now - s["t"] <= window and s["aspect"] >= UPRIGHT:
                return s
        return None

    def low(self, s: dict) -> bool:
        tallest = max((p["h"] for p in self.samples if p["aspect"] >= UPRIGHT), default=0.0)
        return s["aspect"] <= LOW_ASPECT or (tallest > 0.0 and s["h"] <= tallest * LOW_SHRINK)

    def confidence(self) -> float:
        recent = [s["score"] for s in self.samples[::-1][:5]]
        if not recent:
            return 0.0
        return min(1.0, max(0.0, sum(recent) / len(recent) * 0.9))


class PyPosture:
    def __init__(self, **config) -> None:
        merged = {**DEFAULTS, **config}
        if set(merged) != set(DEFAULTS) or not all(_finite(merged[k]) and LIMITS[k][0] <= merged[k] <= LIMITS[k][1]
                                                   for k in DEFAULTS):
            raise ValueError("rescue.posture.config")
        self.config = merged
        self.cameras: dict[str, dict] = {}

    def tracks(self, camera: str) -> int:
        return len(self.cameras.get(camera, {}).get("tracks", []))

    def observe(self, camera: str, t: float, fw: float, fh: float, bodies: list) -> list[tuple]:
        if len(bodies) > MAX_BODIES * 4:
            raise ValueError("rescue.posture.too_many")
        frame_ok = _finite(fw, fh) and 16.0 <= fw <= 16_384.0 and 16.0 <= fh <= 16_384.0
        if not isinstance(camera, str) or not LABEL.match(camera) or not _finite(t) or t < 0.0 or not frame_ok:
            return []
        if camera not in self.cameras and len(self.cameras) >= MAX_CAMERAS:
            return []
        cfg = self.config
        cam = self.cameras.setdefault(camera, {"tracks": [], "next": 0})
        cam["tracks"] = [tr for tr in cam["tracks"] if tr.samples and t - tr.samples[-1]["t"] <= cfg["max_gap_s"]
                         and tr.samples[-1]["t"] <= t]
        samples = [s for s in (_sample(b, fw, fh, t) for b in bodies[:MAX_BODIES]) if s is not None]
        taken = [False] * len(cam["tracks"])
        events: list[tuple] = []
        for s in samples:
            best = None
            for i, tr in enumerate(cam["tracks"]):
                if taken[i] or not tr.samples:
                    continue
                iou = _iou(tr.samples[-1], s)
                if iou >= MATCH_IOU and (best is None or iou >= best[1]):
                    best = (i, iou)
            if best is not None:
                index = best[0]
            elif len(cam["tracks"]) < MAX_TRACKS:
                cam["next"] = (cam["next"] + 1) & 0xFFFFFFFF
                cam["tracks"].append(Track(cam["next"]))
                taken.append(False)
                index = len(cam["tracks"]) - 1
            else:
                continue
            taken[index] = True
            self._step(cam["tracks"][index], s, camera, events)
        return events

    def _step(self, track: Track, s: dict, camera: str, events: list) -> None:
        cfg = self.config
        track.samples.append(s)
        while len(track.samples) > MAX_SAMPLES or (track.samples and s["t"] - track.samples[0]["t"] > HISTORY_S):
            track.samples.pop(0)
        if s["aspect"] >= UPRIGHT:
            track.candidate, track.fell, track.fall_sent, track.anchor, track.immobile_sent = None, False, False, None, False
            return
        if not track.low(s):
            track.candidate, track.anchor = None, None
            return
        if track.candidate is None and not track.fall_sent:
            r = track.upright_ref(s["t"], cfg["fall_window_s"])
            if r is not None:
                drop = (s["top"] - r["top"]) / max(r["h"], 1e-6)
                if drop >= MIN_DROP:
                    speed = min(1.0, max(0.0, (cfg["fall_window_s"] - (s["t"] - r["t"])) / cfg["fall_window_s"]))
                    size = min(1.0, max(0.0, (drop - MIN_DROP) / 0.4))
                    p = 0.55 + 0.25 * size + 0.15 * speed
                    if s["rest"]:
                        p *= 0.5
                    track.candidate = (s["t"], min(0.95, max(0.0, p)))
        if track.candidate is not None:
            since, p = track.candidate
            if not track.fall_sent and s["t"] - since >= cfg["confirm_s"]:
                track.fall_sent = True
                track.fell = True
                events.append((camera, track.id, "fall", p, track.confidence(), since))
        if s["rest"] and not track.fell:
            track.anchor = None
            return
        a = track.anchor
        if a is None or math.sqrt((s["cx"] - a["cx"]) ** 2 + (s["cy"] - a["cy"]) ** 2) > cfg["still_frac"]:
            track.anchor = s
            return
        if not track.immobile_sent and s["t"] - a["t"] >= cfg["immobile_s"]:
            track.immobile_sent = True
            events.append((camera, track.id, "immobility", 0.9 if track.fell else 0.7, track.confidence(), s["t"]))
