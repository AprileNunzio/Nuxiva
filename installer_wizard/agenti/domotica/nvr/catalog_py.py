import bisect
import json
import re

ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
TIERS = ("continuous", "event", "pinned")
RANK = {"continuous": 0, "event": 1, "pinned": 2}
FIELDS = ("id", "camera", "start_ms", "duration_ms", "bytes", "tier", "audio", "video")
MAX_SEGMENTS = 4_000_000
MAX_DURATION_MS = 3_600_000
LOOK_BACK = 8
MAX_LIMIT = 20_000


def _dump(value) -> str:
    return json.dumps(value, separators=(",", ":"))


def _segment(raw: dict) -> dict:
    seg = {k: raw[k] for k in FIELDS}
    ok = (all(isinstance(seg[k], str) and ID.match(seg[k]) for k in ("id", "camera"))
          and all(type(seg[k]) is int and seg[k] >= 0 for k in ("start_ms", "duration_ms", "bytes"))
          and 0 < seg["duration_ms"] <= MAX_DURATION_MS and seg["tier"] in TIERS
          and all(type(seg[k]) is bool for k in ("audio", "video")))
    if not ok:
        raise ValueError("nvr.segment.invalid")
    return seg


def _end(seg: dict) -> int:
    return seg["start_ms"] + seg["duration_ms"]


class PyNvrCatalog:
    def __init__(self) -> None:
        self.lines: dict[str, dict[int, dict]] = {}
        self.starts: dict[str, list[int]] = {}
        self.ids: dict[tuple, int] = {}

    @staticmethod
    def from_json(text: str) -> "PyNvrCatalog":
        rows = json.loads(text)
        if not isinstance(rows, list) or len(rows) > MAX_SEGMENTS:
            raise ValueError("nvr.catalog.corrupt")
        out = PyNvrCatalog()
        for row in rows:
            out.insert(_dump(row))
        return out

    def to_json(self) -> str:
        return _dump(list(self._iter()))

    def __len__(self) -> int:
        return len(self.ids)

    def _iter(self):
        for camera in sorted(self.lines):
            for start in self.starts[camera]:
                yield self.lines[camera][start]

    def insert(self, segment_json: str) -> None:
        seg = _segment(json.loads(segment_json))
        key = (seg["camera"], seg["id"])
        if key not in self.ids and len(self.ids) >= MAX_SEGMENTS:
            raise ValueError("nvr.catalog.too_many")
        self.remove(*key)
        line = self.lines.setdefault(seg["camera"], {})
        starts = self.starts.setdefault(seg["camera"], [])
        previous = line.get(seg["start_ms"])
        if previous is not None:
            self.ids.pop((previous["camera"], previous["id"]), None)
        else:
            bisect.insort(starts, seg["start_ms"])
        line[seg["start_ms"]] = seg
        self.ids[key] = seg["start_ms"]

    def remove(self, camera: str, id_: str) -> str | None:
        start = self.ids.pop((camera, id_), None)
        if start is None:
            return None
        seg = self.lines[camera].pop(start)
        starts = self.starts[camera]
        del starts[bisect.bisect_left(starts, start)]
        if not starts:
            del self.lines[camera], self.starts[camera]
        return _dump(seg)

    def get(self, camera: str, id_: str) -> str | None:
        start = self.ids.get((camera, id_))
        return None if start is None else _dump(self.lines[camera][start])

    def set_tier(self, camera: str, id_: str, tier: str) -> None:
        if tier not in TIERS:
            raise ValueError("nvr.tier.invalid")
        start = self.ids.get((camera, id_))
        if start is None:
            raise ValueError("nvr.segment.not_found")
        self.lines[camera][start]["tier"] = tier

    def _range(self, camera: str, from_ms: int, to_ms: int, limit: int) -> list[dict]:
        if not ID.match(camera):
            raise ValueError("nvr.id.invalid")
        starts = self.starts.get(camera)
        if not starts or to_ms <= from_ms or limit <= 0:
            return []
        line = self.lines[camera]
        cut = bisect.bisect_right(starts, from_ms)
        before = [line[s] for s in starts[max(0, cut - LOOK_BACK):cut] if _end(line[s]) > from_ms and line[s]["start_ms"] < to_ms]
        after = [line[s] for s in starts[cut:bisect.bisect_left(starts, to_ms)]]
        return (before + after)[:limit]

    def range(self, camera: str, from_ms: int, to_ms: int, limit: int) -> str:
        return _dump(self._range(camera, from_ms, to_ms, min(limit, MAX_LIMIT)))

    def seek(self, camera: str, at_ms: int) -> str | None:
        starts = self.starts.get(camera)
        if not starts:
            return None
        line = self.lines[camera]
        cut = bisect.bisect_right(starts, at_ms)
        for s in reversed(starts[max(0, cut - LOOK_BACK):cut]):
            if _end(line[s]) > at_ms:
                return _dump({"segment": line[s], "offset_ms": at_ms - s, "gap_ms": 0})
        if cut >= len(starts):
            return None
        nxt = line[starts[cut]]
        return _dump({"segment": nxt, "offset_ms": 0, "gap_ms": nxt["start_ms"] - at_ms})

    def after(self, camera: str, id_: str) -> str | None:
        start = self.ids.get((camera, id_))
        if start is None:
            return None
        starts = self.starts[camera]
        cut = bisect.bisect_right(starts, start)
        return _dump(self.lines[camera][starts[cut]]) if cut < len(starts) else None

    def spans(self, camera: str, from_ms: int, to_ms: int, tolerance_ms: int) -> str:
        return _dump(spans(self._range(camera, from_ms, to_ms, MAX_LIMIT), tolerance_ms))

    def summary(self) -> str:
        out = []
        for camera in sorted(self.lines):
            segs = [self.lines[camera][s] for s in self.starts[camera]]
            out.append({"camera": camera, "segments": len(segs), "bytes": sum(s["bytes"] for s in segs),
                        "first_ms": segs[0]["start_ms"], "last_ms": max(_end(s) for s in segs),
                        "audio_segments": sum(1 for s in segs if s["audio"])})
        return _dump(out)

    def total_bytes(self) -> int:
        return sum(s["bytes"] for s in self._iter())

    def plan(self, policy_json: str, events_json: str, now_ms: int) -> str:
        policy = json.loads(policy_json)
        events: dict[str, list[int]] = {}
        for camera, at in json.loads(events_json):
            events.setdefault(camera, []).append(int(at))
        for times in events.values():
            times.sort()
        out = {"promote": [], "expire": [], "evict": [], "kept_bytes": 0}
        alive = []
        for seg in self._iter():
            tier = seg["tier"]
            times = events.get(seg["camera"], [])
            low, high = seg["start_ms"] - policy["event_pad_ms"], _end(seg) + policy["event_pad_ms"]
            i = bisect.bisect_left(times, max(0, low))
            promoted = tier == "continuous" and i < len(times) and times[i] <= high
            tier = "event" if promoted else tier
            key = [seg["camera"], seg["id"]]
            age = max(0, now_ms - _end(seg))
            overrides = policy.get("continuous_overrides") or {}
            limit = {"continuous": overrides.get(seg["camera"], policy["continuous_ms"]), "event": policy["event_ms"]}.get(tier)
            if limit is not None and age > limit:
                out["expire"].append(key)
                continue
            if promoted:
                out["promote"].append(key)
            alive.append((tier, seg))
        total = sum(s["bytes"] for _, s in alive)
        if policy["quota_bytes"] > 0 and total > policy["quota_bytes"]:
            candidates = sorted((x for x in alive if x[0] != "pinned"),
                                key=lambda x: (RANK[x[0]], x[1]["start_ms"], x[1]["camera"], x[1]["id"]))
            evicted = set()
            for _, seg in candidates:
                if total <= policy["quota_bytes"]:
                    break
                total -= seg["bytes"]
                evicted.add((seg["camera"], seg["id"]))
                out["evict"].append([seg["camera"], seg["id"]])
            out["promote"] = [k for k in out["promote"] if tuple(k) not in evicted]
        out["kept_bytes"] = total
        return _dump(out)


def spans(segments: list[dict], tolerance_ms: int) -> list[dict]:
    out: list[dict] = []
    for seg in sorted(segments, key=lambda s: s["start_ms"]):
        if out and seg["start_ms"] <= out[-1]["end_ms"] + tolerance_ms:
            last = out[-1]
            last["end_ms"] = max(last["end_ms"], _end(seg))
            last["segments"] += 1
            last["audio"] = last["audio"] or seg["audio"]
            continue
        out.append({"start_ms": seg["start_ms"], "end_ms": _end(seg), "segments": 1, "audio": seg["audio"]})
    return out


def next_marker(markers_json: str, at_ms: int, forward: bool, kinds: list[str]) -> str | None:
    rows = [m for m in json.loads(markers_json) if not kinds or m["kind"] in kinds]
    if forward:
        hits = [m for m in rows if m["at_ms"] > at_ms]
        best = min(hits, key=lambda m: (m["at_ms"], m["id"]), default=None)
    else:
        hits = [m for m in rows if m["at_ms"] < at_ms]
        best = max(hits, key=lambda m: (m["at_ms"], m["id"]), default=None)
    if best is None:
        return None
    return _dump({"at_ms": best["at_ms"], "camera": best["camera"], "kind": best["kind"], "id": best["id"],
                  "label": best["label"], "score": float(best.get("score", 0.0))})
