from dataclasses import dataclass
from typing import Dict, List, Tuple

GROUND_NAMES = {"gnd", "0", "vss", "agnd", "dgnd"}


@dataclass
class _Track:
    track_id: int
    label: str
    bbox: List[float]
    score: float
    hits: int
    missed: int

    def as_dict(self) -> Dict[str, object]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "bbox": self.bbox,
            "score": self.score,
            "hits": self.hits,
            "missed": self.missed,
        }


def normalize_box(bbox: List[float]) -> List[float]:
    x1, y1, x2, y2 = (min(max(float(v), 0.0), 1.0) for v in bbox)
    return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]


def iou(left: List[float], right: List[float]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    width = max(min(lx2, rx2) - max(lx1, rx1), 0.0)
    height = max(min(ly2, ry2) - max(ly1, ry1), 0.0)
    inter = width * height
    union = (lx2 - lx1) * (ly2 - ly1) + (rx2 - rx1) * (ry2 - ry1) - inter
    return 0.0 if union <= 1e-12 else inter / union


class PythonStabilityGate:
    def __init__(self, threshold: float = 6.0, required: int = 3) -> None:
        self._previous: List[int] = []
        self._threshold = max(threshold, 0.0)
        self._required = max(required, 1)
        self._stable = 0
        self._state = "warmup"

    def observe(self, grid: List[int]) -> str:
        if not grid or len(self._previous) != len(grid):
            self._previous = list(grid)
            self._stable = 0
            self._state = "warmup"
            return self._state
        motion = sum(abs(a - b) for a, b in zip(self._previous, grid)) / len(grid)
        self._previous = list(grid)
        if motion > self._threshold:
            self._stable = 0
            self._state = "operator_working"
        else:
            self._stable += 1
            if self._stable >= self._required:
                self._state = "stable_board"
        return self._state

    def reset(self) -> None:
        self._previous = []
        self._stable = 0
        self._state = "warmup"


class PythonComponentTracker:
    def __init__(self, iou_threshold: float = 0.3, smoothing: float = 0.4, max_missed: int = 5) -> None:
        self._tracks: List[_Track] = []
        self._next_id = 1
        self._iou = iou_threshold
        self._alpha = min(max(smoothing, 0.01), 1.0)
        self._max_missed = max_missed

    def update(self, detections: List[Dict[str, object]]) -> List[Dict[str, object]]:
        claimed: List[int] = []
        unmatched: List[Tuple[str, List[float], float]] = []
        for detection in detections:
            label = str(detection["label"])
            box = normalize_box(list(detection["bbox"]))
            score = float(detection.get("score", 0.0))
            index = self._best(label, box, claimed)
            if index is None:
                unmatched.append((label, box, score))
                continue
            claimed.append(index)
            track = self._tracks[index]
            track.bbox = [o + self._alpha * (n - o) for o, n in zip(track.bbox, box)]
            track.score = score
            track.hits += 1
            track.missed = 0
        for index, track in enumerate(self._tracks):
            if index not in claimed:
                track.missed += 1
        self._tracks = [t for t in self._tracks if t.missed <= self._max_missed]
        for label, box, score in unmatched:
            self._tracks.append(_Track(self._next_id, label, box, score, 1, 0))
            self._next_id += 1
        return [t.as_dict() for t in self._tracks]

    def _best(self, label: str, box: List[float], claimed: List[int]):
        best, best_value = None, 0.0
        for index, track in enumerate(self._tracks):
            if index in claimed or track.label != label:
                continue
            value = iou(track.bbox, box)
            if value >= self._iou and (best is None or value > best_value):
                best, best_value = index, value
        return best

    def relabel(self, track_id: int, label: str) -> bool:
        for track in self._tracks:
            if track.track_id == track_id:
                track.label = label
                return True
        return False

    def reset(self) -> None:
        self._tracks = []
        self._next_id = 1


def validate_netlist(nets: List[Dict[str, object]]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if nets and not any(str(n["name"]).strip().lower() in GROUND_NAMES for n in nets):
        issues.append({"kind": "missing_ground", "net": "", "detail": ""})
    owners: Dict[Tuple[str, str], str] = {}
    for net in nets:
        name = str(net["name"])
        pins = list(net["pins"])
        if len(pins) < 2:
            issues.append({"kind": "dangling_net", "net": name, "detail": ""})
        for pin in pins:
            key = (str(pin["reference"]), str(pin["pin"]))
            owner = owners.get(key)
            if owner is None:
                owners[key] = name
            elif owner != name:
                issues.append({
                    "kind": "pin_on_multiple_nets",
                    "net": name,
                    "detail": f"{key[0]}:{key[1]}<->{owner}",
                })
    return issues
