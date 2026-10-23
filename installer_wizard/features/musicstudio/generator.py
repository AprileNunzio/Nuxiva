import random
import time

from features.musicstudio import catalog as C, genres, patterns as P, schema as S, theory as T

FORM = (("intro", 1), ("verse", 2), ("chorus", 2), ("verse", 2), ("chorus", 2), ("bridge", 1), ("chorus", 2), ("outro", 1))
SHORT = (("verse", 1), ("chorus", 1))
PRESENCE = {
    "drums": {"intro": 1, "verse": 2, "chorus": 2, "bridge": 1, "outro": 1}, "bass": {"intro": 0, "verse": 2, "chorus": 2, "bridge": 1, "outro": 0},
    "chords": {"intro": 1, "verse": 2, "chorus": 2, "bridge": 2, "outro": 1}, "pad": {"intro": 2, "verse": 1, "chorus": 2, "bridge": 2, "outro": 2},
    "lead": {"intro": 0, "verse": 0, "chorus": 2, "bridge": 1, "outro": 0}, "arp": {"intro": 1, "verse": 0, "chorus": 2, "bridge": 1, "outro": 0},
    "fx": {"intro": 0, "verse": 1, "chorus": 0, "bridge": 1, "outro": 0}, "vocal": {"intro": 0, "verse": 2, "chorus": 2, "bridge": 2, "outro": 0},
}
TRACK_FX = {
    "drums": (("compressor", {"threshold": -14, "ratio": 3}),), "bass": (("compressor", {"threshold": -20, "ratio": 4}),),
    "chords": (("chorus", {"mix": 0.3}), ("reverb", {"size": 1.6, "mix": 0.18})), "pad": (("reverb", {"size": 3.2, "mix": 0.4}),),
    "lead": (("delay", {"time": 0.375, "feedback": 0.35, "mix": 0.22}), ("reverb", {"size": 2.2, "mix": 0.2})), "arp": (("delay", {"time": 0.1875, "feedback": 0.4, "mix": 0.3}),),
    "vocal": (("compressor", {"threshold": -22, "ratio": 3}), ("reverb", {"size": 1.4, "mix": 0.16})), "fx": (),
}
LEVELS = {"drums": 0.9, "bass": 0.85, "chords": 0.62, "pad": 0.5, "lead": 0.62, "arp": 0.45, "vocal": 1.0, "fx": 0.4}
def _step(pattern: str, i: int) -> str:
    return pattern[i % len(pattern)]


MINOR_HINT = ("triste", "dark", "oscur", "malinc", "sad", "notte", "night", "minor", "epic", "cinemat", "dramm")


def sections(bars: int) -> list[dict]:
    form = FORM if bars >= 12 else SHORT
    weight = sum(w for _, w in form)
    out, start = [], 0
    for index, (name, w) in enumerate(form):
        length = max(1, round(bars * w / weight)) if index < len(form) - 1 else max(1, bars - start)
        length = min(length, bars - start)
        if length <= 0:
            break
        out.append({"name": name, "start": start, "bars": length})
        start += length
    return out


def _label(section: dict, role: str) -> str:
    return f"{section['name']} · {role}"


def _bar_steps(project: dict) -> int:
    return project["beats"] * 4


def _clip(project: dict, section: dict, role: str, notes: list[dict]) -> dict:
    return S.clean_clip({"name": _label(section, role), "start": section["start"] * project["beats"], "length": section["bars"] * project["beats"], "notes": notes})


def _hit(step: int, pitch: int, vel: float, length: float = 0.25) -> dict:
    return {"t": step * 0.25, "d": length, "p": pitch, "v": vel}


def drum_clip(project: dict, section: dict, rng: random.Random, level: int) -> dict:
    kit = P.DRUMS[project["genre"]]
    lanes = {n: p for n, p in kit.items() if level == 2 or n in ("hat", "perc", "rim", "open_hat")}
    notes = []
    per = _bar_steps(project)
    for b in range(section["bars"]):
        base = b * per
        for lane, pattern in lanes.items():
            for i in range(per):
                ch = _step(pattern, i)
                if ch == ".":
                    continue
                vel = {"X": 0.95, "x": 0.72, "o": 0.42}[ch] * (0.7 if level == 1 else 1) * rng.uniform(0.9, 1.05)
                notes.append(_hit(base + i, C.LANES[lane], min(1.0, vel)))
        if level == 2 and b == section["bars"] - 1 and section["name"] != "outro":
            for k in range(4):
                notes.append(_hit(base + per - 4 + k, C.LANES["snare"], 0.5 + 0.12 * k))
        if level == 2 and b == 0 and section["name"] == "chorus":
            notes.append(_hit(base, C.LANES["crash"], 0.9, 1.0))
    return _clip(project, section, "drums", notes)


def bass_clip(project: dict, section: dict, rng: random.Random, level: int) -> dict:
    pattern = P.BASS[project["genre"]]
    per = _bar_steps(project)
    notes = []
    for b in range(section["bars"]):
        chord = T.chord_at(project["harmony"], section["start"] + b)
        root = 36 + chord["root"]
        marks = [i for i in range(per) if _step(pattern, i) not in ".-"]
        if level == 1:
            marks = marks[::2] or marks[:1]
        for n, i in enumerate(marks):
            end = marks[n + 1] if n + 1 < len(marks) else per
            kind = _step(pattern, i)
            pitch = root + {"r": 0, "f": 7, "o": 12}.get(kind, 0)
            notes.append(_hit(b * per + i, pitch, rng.uniform(0.78, 0.95), max(0.25, (end - i) * 0.25 * 0.92)))
    return _clip(project, section, "bass", notes)


def chord_clip(project: dict, section: dict, rng: random.Random, level: int, role: str) -> dict:
    per = _bar_steps(project)
    notes = []
    if role == "pad":
        b = 0
        while b < section["bars"]:
            chord = T.chord_at(project["harmony"], section["start"] + b)
            span = 1
            while b + span < section["bars"] and T.chord_at(project["harmony"], section["start"] + b + span) == chord:
                span += 1
            for pitch in T.voicing(chord, 60, 4):
                notes.append({"t": b * project["beats"], "d": span * project["beats"] * 0.98, "p": pitch, "v": rng.uniform(0.5, 0.65)})
            b += span
        return _clip(project, section, role, notes)
    pattern = P.COMP[project["genre"]]
    for b in range(section["bars"]):
        chord = T.chord_at(project["harmony"], section["start"] + b)
        marks = [i for i in range(per) if _step(pattern, i) == "c"]
        if level == 1:
            marks = marks[:1]
        for n, i in enumerate(marks):
            end = marks[n + 1] if n + 1 < len(marks) else per
            for pitch in T.voicing(chord, 62, 4 if "7" in chord["quality"] else 3):
                notes.append(_hit(b * per + i, pitch, rng.uniform(0.55, 0.72), max(0.25, (end - i) * 0.25 * 0.9)))
    return _clip(project, section, role, notes)


def arp_clip(project: dict, section: dict, rng: random.Random, level: int) -> dict:
    per = _bar_steps(project)
    notes = []
    order = rng.choice(((0, 1, 2, 1), (0, 1, 2, 3, 2, 1), (0, 2, 1, 2)))
    for b in range(section["bars"]):
        chord = T.chord_at(project["harmony"], section["start"] + b)
        tones = T.voicing(chord, 72, 3) + [p + 12 for p in T.voicing(chord, 72, 3)]
        for i in range(0, per, 2 if level == 1 else 1):
            notes.append(_hit(b * per + i, tones[order[(i // (2 if level == 1 else 1)) % len(order)] % len(tones)], rng.uniform(0.45, 0.7), 0.22))
    return _clip(project, section, "arp", notes)


def lead_clip(project: dict, section: dict, rng: random.Random, level: int) -> dict:
    per = _bar_steps(project)
    key = project["key"]
    scale = T.scale_pitches(key["root"], key["mode"], 64, 88)
    rhythm = rng.choice(P.RHYTHMS)
    contour = [rng.choice((-2, -1, 0, 1, 2)) for _ in range(8)]
    notes = []
    index = len(scale) // 2
    count = 0
    for b in range(section["bars"]):
        chord = T.chord_at(project["harmony"], section["start"] + b)
        tones = {(chord["root"] + i) % 12 for i in T.INTERVALS[chord["quality"]]}
        marks = [i for i in range(per) if _step(rhythm, i) == "x"]
        if level == 1:
            marks = marks[::2] or marks[:1]
        for n, i in enumerate(marks):
            index = max(0, min(len(scale) - 1, index + contour[count % len(contour)]))
            count += 1
            if i % 4 == 0:
                index = min(range(len(scale)), key=lambda k: (scale[k] % 12 not in tones, abs(k - index)))
            end = marks[n + 1] if n + 1 < len(marks) else per
            notes.append(_hit(b * per + i, scale[index], rng.uniform(0.7, 0.92), max(0.25, (end - i) * 0.25 * 0.85)))
    return _clip(project, section, "lead", notes)


def fx_clip(project: dict, section: dict, rng: random.Random, level: int) -> dict:
    return _clip(project, section, "fx", [{"t": max(0, section["bars"] - 2) * project["beats"], "d": min(2, section["bars"]) * project["beats"], "p": 60, "v": 0.7}])


BUILDERS = {"drums": drum_clip, "bass": bass_clip, "lead": lead_clip, "arp": arp_clip, "fx": fx_clip}


def default_instrument(project: dict, role: str) -> str:
    genre = project["genre"]
    style = genres.get(genre)
    pick = {"drums": style.kit, "bass": style.bass_i, "chords": style.chords_i, "lead": style.lead_i, "pad": style.pad_i, "arp": style.arp_i}.get(role)
    return pick or C.DEFAULT_INSTRUMENT[role]


def build_track(project: dict, role: str, rng: random.Random, instrument: str = "") -> dict:
    clips = []
    for section in project["structure"]:
        level = PRESENCE[role].get(section["name"], 1)
        if not level:
            continue
        if role in ("chords", "pad"):
            clip = chord_clip(project, section, rng, level, role)
        else:
            clip = BUILDERS[role](project, section, rng, level)
        if role == "fx" and section["name"] not in ("verse", "bridge"):
            continue
        if clip["notes"]:
            clips.append(clip)
    inst = instrument if instrument in C.BY_ID and C.BY_ID[instrument].role == (role if role != "pad" else "pad") else default_instrument(project, role)
    return S.clean_track({"role": role, "instrument": inst, "volume": LEVELS[role], "clips": clips,
                          "effects": [{"type": t, "params": p} for t, p in TRACK_FX.get(role, ())], "pan": {"arp": 0.3, "chords": -0.15, "pad": 0.0}.get(role, 0.0)})


def lyric_clips(project: dict, lyrics: str, lang: str, voice: str) -> list[dict]:
    stanzas = [s.strip() for s in lyrics.replace("\r", "").split("\n\n") if s.strip()] or ([lyrics.strip()] if lyrics.strip() else [])
    spots = [s for s in project["structure"] if s["name"] in ("verse", "chorus", "bridge")]
    clips = []
    for stanza, section in zip(stanzas, spots):
        clips.append({"name": _label(section, "vocal"), "start": section["start"] * project["beats"], "length": section["bars"] * project["beats"], "notes": [],
                      "vocal": {"text": stanza, "lang": lang, "voice": voice, "speed": 1.0, "pitch": 0}})
    return clips


def vocal_track(project: dict, lyrics: str, lang: str, voice: str = "") -> dict:
    return S.clean_track({"role": "vocal", "instrument": "voice_tts", "name": "Voce", "volume": LEVELS["vocal"], "clips": lyric_clips(project, lyrics, lang, voice),
                          "effects": [{"type": t, "params": p} for t, p in TRACK_FX["vocal"]]})


def arrange(spec: dict) -> dict:
    rng = random.Random(spec.get("seed") or secrets_seed())
    style = genres.get(spec.get("genre"))
    genre = style.id
    low, high = style.tempo
    mood = str(spec.get("mood") or spec.get("title") or "").lower()
    if spec.get("mode") in C.MODES:
        mode = spec["mode"]
    elif style.mode not in ("major", "minor"):
        mode = style.mode
    else:
        mode = "minor" if style.mode == "minor" or any(h in mood for h in MINOR_HINT) else "major"
    project = S.clean_project({"title": spec.get("title") or "", "prompt": spec.get("prompt") or "", "created": int(time.time()), "genre": genre,
                               "tempo": spec.get("tempo") or rng.randint(low, high), "beats": spec.get("beats") or style.beats,
                               "key": {"root": spec.get("root") if isinstance(spec.get("root"), int) else rng.randrange(12), "mode": mode},
                               "bars": spec.get("bars") or 32, "swing": style.swing})
    project["structure"] = sections(project["bars"])
    slow = 2 if style.family in ("cinematic",) or genre in ("ballad", "ambient", "newage", "sacred_choir") else 1
    project["harmony"] = (T.named(project["key"]["root"], project["bars"], style.prog, slow) if style.prog
                          else T.harmony(project["key"]["root"], mode, project["bars"], rng, style.seventh, slow))
    wanted = [r for r in (spec.get("roles") or style.roles) if r in PRESENCE and r != "vocal"]
    instruments = spec.get("instruments") if isinstance(spec.get("instruments"), dict) else {}
    project["tracks"] = [build_track(project, role, rng, instruments.get(role, "")) for role in wanted]
    return S.clean_project(project, project["id"])


def secrets_seed() -> int:
    return random.SystemRandom().randrange(1 << 30)


def add_layer(project: dict, role: str, instrument: str = "", seed: int = 0) -> dict:
    if role not in PRESENCE or role == "vocal":
        raise S.SpecError("role_invalid")
    if len(project["tracks"]) >= S.MAX_TRACKS:
        raise S.SpecError("tracks_full")
    track = build_track(project, role, random.Random(seed or secrets_seed()), instrument)
    taken = sum(1 for t in project["tracks"] if t["role"] == role)
    if taken:
        track["name"] = f"{track['name']} {taken + 1}"
    return track
