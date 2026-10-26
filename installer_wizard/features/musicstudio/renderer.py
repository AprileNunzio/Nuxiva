import io
import wave

import numpy as np

from features.musicstudio import catalog, dsp_fx, dsp_voices, schema as S, store
from features.musicstudio.dsp import SR

MAX_SECONDS = 900
TAIL = 3.0
LANE_BY_MIDI = {midi: lane for lane, midi in catalog.LANES.items()}


class RenderError(ValueError):
    pass


def _load_asset(pid: str, name: str) -> np.ndarray | None:
    try:
        with wave.open(str(store.audio_dir(pid) / name), "rb") as clip:
            channels, width, rate, frames = clip.getnchannels(), clip.getsampwidth(), clip.getframerate(), clip.getnframes()
            raw = clip.readframes(frames)
    except (OSError, wave.Error, EOFError, KeyError):
        return None
    if width != 2 or not frames:
        return None
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    data = data.reshape(-1, channels).mean(axis=1)
    if rate != SR:
        data = np.interp(np.linspace(0, len(data) - 1, int(len(data) * SR / rate)), np.arange(len(data)), data).astype(np.float32)
    return data


def _place(buffer: np.ndarray, sound: np.ndarray, at: float) -> None:
    start = int(at * SR)
    if start >= buffer.shape[-1] or start < 0:
        return
    end = min(buffer.shape[-1], start + len(sound))
    buffer[start:end] += sound[: end - start]


def _track(project: dict, track: dict, total: int, beat: float) -> np.ndarray | None:
    instrument = catalog.BY_ID.get(track["instrument"])
    if instrument is None:
        return None
    mono = np.zeros(total, dtype=np.float32)
    voice = instrument.voice
    engine = voice.get("engine")
    cache: dict[tuple, np.ndarray] = {}
    for clip in track["clips"]:
        base = clip["start"]
        vocal = clip.get("vocal")
        if vocal:
            sound = _load_asset(project["id"], vocal["asset"]) if vocal.get("asset") else None
            if sound is not None:
                _place(mono, sound * 0.9, base * beat)
            continue
        for note in clip["notes"]:
            at = base + note["t"]
            eighth = round(at * 2)
            if abs(at * 2 - eighth) < 0.02 and eighth % 2 == 1:
                at += project["swing"] * 0.17
            velocity = round(note["v"], 2)
            if engine == "drums":
                lane = LANE_BY_MIDI.get(note["p"])
                if lane:
                    key = ("d", lane, velocity)
                    sound = cache.get(key)
                    if sound is None:
                        sound = cache[key] = dsp_voices.drum(voice, lane, velocity)
                    _place(mono, sound, at * beat)
            elif engine == "noise":
                _place(mono, dsp_voices.riser(note["d"] * beat, velocity), at * beat)
            elif engine == "synth":
                length = round(note["d"] * beat, 2)
                key = ("s", note["p"], length, velocity)
                sound = cache.get(key)
                if sound is None:
                    sound = cache[key] = dsp_voices.synth(voice, note["p"], length, velocity)
                _place(mono, sound, at * beat)
    if not mono.any():
        return None
    stereo = np.stack([mono, mono])
    stereo = dsp_fx.chain(stereo, track["effects"], beat)
    angle = (min(1.0, max(-1.0, track["pan"])) + 1) * np.pi / 4
    stereo = stereo * np.array([[np.cos(angle) * 1.414], [np.sin(angle) * 1.414]], dtype=np.float32)
    if track["mute"]:
        return None
    return stereo * float(track["volume"])


def mixdown(project: dict) -> np.ndarray:
    beat = 60.0 / project["tempo"]
    seconds = project["bars"] * project["beats"] * beat
    if seconds > MAX_SECONDS or seconds <= 0:
        raise RenderError("too_long")
    total = int((seconds + TAIL) * SR)
    solo = any(t["solo"] for t in project["tracks"])
    mix = np.zeros((2, total), dtype=np.float32)
    for track in project["tracks"]:
        if solo and not track["solo"]:
            continue
        rendered = _track(project, track, total, beat)
        if rendered is not None:
            mix += rendered
    mix = dsp_fx.chain(mix, project["master"]["effects"], beat) * float(project["master"]["volume"])
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.89:
        mix *= 0.89 / peak
    return mix


def to_wav(mix: np.ndarray) -> bytes:
    pcm = (np.clip(mix, -1.0, 1.0).T * 32767).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(SR)
        target.writeframes(pcm.tobytes())
    return out.getvalue()


def render(project: dict) -> bytes:
    return to_wav(mixdown(S.clean_project(project, project["id"])))
