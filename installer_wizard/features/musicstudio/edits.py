import random

from features.musicstudio import catalog as C, generator, schema as S

MAX_OPS = 8


def find(project: dict, ref) -> dict | None:
    key = str(ref or "").strip().lower()
    if not key:
        return None
    tracks = project["tracks"]
    return (next((t for t in tracks if t["id"] == key), None)
            or next((t for t in tracks if t["name"].lower() == key), None)
            or next((t for t in tracks if t["role"] == key), None)
            or next((t for t in tracks if key in t["name"].lower() or key in t["instrument"]), None))


def _bag(project: dict, ref) -> list[dict]:
    if str(ref or "").lower() in ("master", "mix", "tutto"):
        return project["master"]["effects"]
    track = find(project, ref)
    if track is None:
        raise S.SpecError("track_unknown")
    return track["effects"]


def _track(project: dict, op: dict) -> dict:
    track = find(project, op.get("track"))
    if track is None:
        raise S.SpecError("track_unknown")
    return track


def set_track(project: dict, op: dict) -> str:
    track = _track(project, op)
    if "volume" in op:
        track["volume"] = S.number(op["volume"], 0, 1.5, track["volume"])
    if "pan" in op:
        track["pan"] = S.number(op["pan"], -1, 1, track["pan"])
    for flag in ("mute", "solo"):
        if flag in op:
            track[flag] = bool(op[flag])
    instrument = op.get("instrument")
    if instrument in C.BY_ID and C.BY_ID[instrument].role == track["role"]:
        track["instrument"] = instrument
        track["color"] = C.BY_ID[instrument].color
    return track["name"]


def add_effect(project: dict, op: dict) -> str:
    effects = _bag(project, op.get("track"))
    if op.get("type") not in C.EFFECT_BY_ID:
        raise S.SpecError("effect_invalid")
    if len(effects) >= S.MAX_EFFECTS:
        raise S.SpecError("effects_full")
    fresh = S.clean_effect({"type": op["type"], "params": op.get("params") if isinstance(op.get("params"), dict) else {}})
    effects[:] = [e for e in effects if e["type"] != fresh["type"]] + [fresh]
    return fresh["type"]


def set_effect(project: dict, op: dict) -> str:
    effects = _bag(project, op.get("track"))
    current = next((e for e in effects if e["type"] == op.get("type")), None)
    if current is None:
        return add_effect(project, op)
    merged = S.clean_effect({**current, "params": {**current["params"], **(op.get("params") if isinstance(op.get("params"), dict) else {})}, "on": op.get("on", current["on"])})
    current.update(params=merged["params"], on=merged["on"])
    return current["type"]


def remove_effect(project: dict, op: dict) -> str:
    effects = _bag(project, op.get("track"))
    effects[:] = [e for e in effects if e["type"] != op.get("type")]
    return str(op.get("type"))


def add_layer(project: dict, op: dict) -> str:
    track = generator.add_layer(project, op.get("role"), op.get("instrument") or "")
    project["tracks"].append(track)
    return track["name"]


def remove_track(project: dict, op: dict) -> str:
    track = _track(project, op)
    project["tracks"].remove(track)
    return track["name"]


def regenerate(project: dict, op: dict) -> str:
    track = _track(project, op)
    if track["role"] == "vocal":
        raise S.SpecError("role_invalid")
    fresh = generator.build_track(project, track["role"], random.Random(random.SystemRandom().randrange(1 << 30)), op.get("instrument") or track["instrument"])
    track.update(clips=fresh["clips"], instrument=fresh["instrument"], color=fresh["color"])
    return track["name"]


def set_tempo(project: dict, op: dict) -> str:
    project["tempo"] = S.number(op.get("tempo"), 40, 220, project["tempo"])
    return str(round(project["tempo"]))


def set_swing(project: dict, op: dict) -> str:
    project["swing"] = S.number(op.get("swing"), 0, 0.6, project["swing"])
    return str(project["swing"])


def master(project: dict, op: dict) -> str:
    project["master"]["volume"] = S.number(op.get("volume"), 0, 1.2, project["master"]["volume"])
    return "master"


HANDLERS = {"set_track": set_track, "add_effect": add_effect, "set_effect": set_effect, "remove_effect": remove_effect, "add_layer": add_layer,
            "remove_track": remove_track, "regenerate": regenerate, "set_tempo": set_tempo, "set_swing": set_swing, "master": master}


def apply(project: dict, ops: list) -> list[dict]:
    done = []
    for op in (ops if isinstance(ops, list) else [])[:MAX_OPS]:
        handler = HANDLERS.get(op.get("op")) if isinstance(op, dict) else None
        if handler is None:
            continue
        try:
            done.append({"op": op["op"], "target": handler(project, op)})
        except (S.SpecError, KeyError, TypeError, ValueError):
            continue
    return done
