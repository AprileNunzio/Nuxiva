import re
import secrets

from features.musicstudio import catalog as C

ID_RE = re.compile(r"^[0-9a-f]{8}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TEXT_STRIP = re.compile(r"[^\w .,:;!?'’\-+/&()àèéìòùÀÈÉÌÒÙçÇñÑüÜöÖäÄßœŒ\n]", re.UNICODE)
LANG_RE = re.compile(r"^[a-z]{2}$")
MAX_TRACKS = 24
MAX_CLIPS = 96
MAX_NOTES = 640
MAX_EFFECTS = 8
MAX_BARS = 256
HARMONY_QUALITIES = ("maj", "min", "dim", "dom7", "min7", "maj7", "sus4")


class SpecError(ValueError):
    pass


def new_id() -> str:
    return secrets.token_hex(4)


def text(value, limit: int, keep_lines: bool = False) -> str:
    raw = str(value or "")
    if not keep_lines:
        raw = raw.replace("\n", " ")
    return TEXT_STRIP.sub("", raw).strip()[:limit]


def number(value, low: float, high: float, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):
        return default
    return round(max(low, min(high, v)), 4)


def clean_id(value) -> str:
    return value if isinstance(value, str) and ID_RE.fullmatch(value) else new_id()


def clean_note(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return {"t": number(raw.get("t"), 0, 4096, 0), "d": number(raw.get("d"), 0.0625, 64, 0.5), "p": int(number(raw.get("p"), 0, 127, 60)), "v": number(raw.get("v"), 0.05, 1, 0.8)}


def clean_vocal(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    lang = source.get("lang") if isinstance(source.get("lang"), str) and LANG_RE.fullmatch(source.get("lang")) else "it"
    asset = source.get("asset") if isinstance(source.get("asset"), str) and re.fullmatch(r"[0-9a-f]{8}\.wav", source.get("asset")) else ""
    return {"text": text(source.get("text"), 600, True), "lang": lang, "voice": text(source.get("voice"), 40), "speed": number(source.get("speed"), 0.6, 1.6, 1.0),
            "pitch": number(source.get("pitch"), -12, 12, 0), "asset": asset}


def clean_clip(raw) -> dict:
    if not isinstance(raw, dict):
        raise SpecError("clip_invalid")
    notes = [n for n in (clean_note(r) for r in (raw.get("notes") if isinstance(raw.get("notes"), list) else [])[:MAX_NOTES]) if n]
    clip = {"id": clean_id(raw.get("id")), "name": text(raw.get("name"), 40), "start": number(raw.get("start"), 0, MAX_BARS * 8, 0),
            "length": number(raw.get("length"), 0.25, MAX_BARS * 8, 4), "notes": sorted(notes, key=lambda n: (n["t"], n["p"]))}
    if isinstance(raw.get("vocal"), dict):
        clip["vocal"] = clean_vocal(raw.get("vocal"))
    return clip


def clean_effect(raw) -> dict | None:
    if not isinstance(raw, dict) or raw.get("type") not in C.EFFECT_BY_ID:
        return None
    effect = C.EFFECT_BY_ID[raw["type"]]
    params = raw.get("params") if isinstance(raw.get("params"), dict) else {}
    return {"id": clean_id(raw.get("id")), "type": effect.id, "on": raw.get("on") is not False,
            "params": {k: number(params.get(k), v.low, v.high, v.default) for k, v in effect.knobs.items()}}


def clean_effects(rows) -> list[dict]:
    return [e for e in (clean_effect(r) for r in (rows if isinstance(rows, list) else [])[:MAX_EFFECTS]) if e]


def clean_track(raw) -> dict:
    if not isinstance(raw, dict):
        raise SpecError("track_invalid")
    role = raw.get("role") if raw.get("role") in C.ROLES else "lead"
    instrument = raw.get("instrument") if raw.get("instrument") in C.BY_ID else C.DEFAULT_INSTRUMENT[role]
    color = raw.get("color") if isinstance(raw.get("color"), str) and HEX.fullmatch(raw.get("color")) else C.BY_ID[instrument].color
    clips = []
    for row in (raw.get("clips") if isinstance(raw.get("clips"), list) else [])[:MAX_CLIPS]:
        try:
            clips.append(clean_clip(row))
        except SpecError:
            continue
    return {"id": clean_id(raw.get("id")), "name": text(raw.get("name"), 40) or C.BY_ID[instrument].name, "role": role, "instrument": instrument, "color": color,
            "volume": number(raw.get("volume"), 0, 1.5, 0.8), "pan": number(raw.get("pan"), -1, 1, 0), "mute": bool(raw.get("mute")), "solo": bool(raw.get("solo")),
            "effects": clean_effects(raw.get("effects")), "clips": sorted(clips, key=lambda c: c["start"])}


def clean_key(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    return {"root": int(number(source.get("root"), 0, 11, 0)), "mode": source.get("mode") if source.get("mode") in C.MODES else "major"}


def clean_harmony(rows) -> list[dict]:
    out = []
    for row in (rows if isinstance(rows, list) else [])[:MAX_BARS]:
        if isinstance(row, dict):
            out.append({"bar": int(number(row.get("bar"), 0, MAX_BARS, len(out))), "root": int(number(row.get("root"), 0, 11, 0)),
                        "quality": row.get("quality") if row.get("quality") in HARMONY_QUALITIES else "maj"})
    return out


def clean_structure(rows) -> list[dict]:
    out = []
    for row in (rows if isinstance(rows, list) else [])[:24]:
        if isinstance(row, dict):
            out.append({"name": text(row.get("name"), 24) or "section", "start": int(number(row.get("start"), 0, MAX_BARS, 0)), "bars": int(number(row.get("bars"), 1, MAX_BARS, 4))})
    return out


def clean_lyrics(raw) -> dict:
    source = raw if isinstance(raw, dict) else {}
    translations = source.get("translations") if isinstance(source.get("translations"), dict) else {}
    return {"lang": source.get("lang") if isinstance(source.get("lang"), str) and LANG_RE.fullmatch(source.get("lang")) else "it", "text": text(source.get("text"), 4000, True),
            "translations": {k: text(v, 4000, True) for k, v in list(translations.items())[:12] if isinstance(k, str) and LANG_RE.fullmatch(k)}}


def clean_project(raw, existing_id: str = "") -> dict:
    source = raw if isinstance(raw, dict) else {}
    tracks = []
    for row in (source.get("tracks") if isinstance(source.get("tracks"), list) else [])[:MAX_TRACKS]:
        try:
            tracks.append(clean_track(row))
        except SpecError:
            continue
    master = source.get("master") if isinstance(source.get("master"), dict) else {}
    return {"id": existing_id or clean_id(source.get("id")), "title": text(source.get("title"), 80), "prompt": text(source.get("prompt"), 600),
            "created": int(number(source.get("created"), 0, 4e9, 0)), "revision": int(number(source.get("revision"), 0, 1e9, 0)),
            "tempo": number(source.get("tempo"), 40, 220, 100), "beats": int(number(source.get("beats"), 2, 7, 4)), "swing": number(source.get("swing"), 0, 0.6, 0),
            "key": clean_key(source.get("key")), "genre": source.get("genre") if source.get("genre") in C.GENRES else "pop",
            "bars": int(number(source.get("bars"), 1, MAX_BARS, 16)), "harmony": clean_harmony(source.get("harmony")), "structure": clean_structure(source.get("structure")),
            "lyrics": clean_lyrics(source.get("lyrics")), "tracks": tracks,
            "master": {"volume": number(master.get("volume"), 0, 1.2, 0.9), "effects": clean_effects(master.get("effects"))}}
