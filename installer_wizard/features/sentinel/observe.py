import re

from features.sentinel import memory_people

SAFE = re.compile(r"[^a-z0-9_.-]+")
CLASSES = frozenset({"person", "vehicle", "animal"})
COLORS = frozenset({"black", "white", "grey", "red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink",
                    "brown", "beige"})
ITEMS = frozenset({"backpack", "bag", "parcel", "suitcase", "umbrella", "phone", "trolley"})
VEHICLES = frozenset({"car", "van", "truck", "motorbike", "scooter", "bicycle"})


def token(raw, limit: int = 64) -> str | None:
    value = SAFE.sub("-", str(raw or "").strip().lower()).strip("-")[:limit]
    return value or None


def _color(value) -> str | None:
    return value if value in COLORS else None


def _box(raw) -> list[float] | None:
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    try:
        box = [float(v) for v in raw]
    except (TypeError, ValueError):
        return None
    return box if all(0.0 <= v <= 1.0 for v in box) else None


def _look(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    items = sorted({i for i in raw.get("carrying") or [] if i in ITEMS})
    look = {"upper": _color(raw.get("upper")), "lower": _color(raw.get("lower")), "carrying": items}
    if isinstance(raw.get("hi_vis"), bool):
        look["hi_vis"] = raw["hi_vis"]
    return look


def identities(presence: dict) -> list[tuple[float, float, str]]:
    out = []
    for p in (presence or {}).get("people") or []:
        gaze, slug = p.get("gaze") or {}, p.get("slug")
        if not slug or not isinstance(gaze, dict):
            continue
        try:
            out.append((float(gaze.get("x")), float(gaze.get("y")), str(slug)))
        except (TypeError, ValueError):
            continue
    return out


def _slug(faces: list | None, box: list[float]) -> str | None:
    x, y, w, h = box
    hits = [slug for fx, fy, slug in faces or [] if x <= fx <= x + w and y <= fy <= y + h * 0.45]
    return hits[0] if len(hits) == 1 else None


def _identity(slug: str | None, profiles: dict) -> tuple[dict | None, bool]:
    if slug is None:
        return None, memory_people.allows_details(None)
    if slug not in profiles:
        profiles[slug] = memory_people._profile(slug)
    profile = profiles[slug]
    if profile is None:
        return None, memory_people.allows_details(None)
    return memory_people.who_for(slug, profile), memory_people.allows_details(profile)


def observations(source: dict, result: dict, at_ms: int, faces: list | None = None) -> list[dict]:
    camera = token(source.get("id"))
    if camera is None:
        return []
    zone = token(source.get("room"))
    profiles: dict = {}
    out = []
    for body in (result or {}).get("bodies") or []:
        if not isinstance(body, dict) or body.get("class") not in CLASSES:
            continue
        box = _box(body.get("box"))
        if box is None:
            continue
        try:
            score = max(0.0, min(1.0, float(body.get("score", 0.0))))
        except (TypeError, ValueError):
            continue
        row = {"camera": camera, "zone": zone, "at_ms": at_ms, "class": body["class"], "box": box, "score": score}
        if body["class"] == "person":
            row["look"] = _look(body.get("look"))
            who, details = _identity(_slug(faces, box), profiles)
            if who is not None:
                row["who"] = who
            if not details:
                row["look"] = {}
            elif isinstance(body.get("gait"), list) and len(body["gait"]) == 16:
                try:
                    row["gait"] = [float(v) for v in body["gait"]]
                except (TypeError, ValueError):
                    pass
        elif body["class"] == "vehicle":
            vehicle = body.get("vehicle") or {}
            if vehicle.get("kind") not in VEHICLES:
                continue
            row["vehicle"] = {"kind": vehicle["kind"], "color": _color(vehicle.get("color"))}
        out.append(row)
    return out

