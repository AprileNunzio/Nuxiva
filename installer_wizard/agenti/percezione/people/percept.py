import json
import logging
import threading
import time
import uuid

from agenti.people import hot

log = logging.getLogger("nuxiva.people.percept")
_lock = threading.Lock()
_state = {"ctx": None, "fusion": None}


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustPercept", None)


def enabled() -> bool:
    return hot.enabled() and _native() is not None


def _fusion():
    ctx = hot._ready()
    with _lock:
        if _state["ctx"] is not ctx or _state["fusion"] is None:
            _state.update(ctx=ctx, fusion=_native()(ctx))
        return _state["fusion"]


def _now(now_ms: int | None) -> int:
    return int(time.time() * 1000) if now_ms is None else now_ms


def _permille(confidence: float) -> int:
    return max(0, min(1000, round(float(confidence) * 1000)))


def _send(observation: dict, now_ms: int) -> None:
    _fusion().observe(json.dumps(observation, separators=(",", ":")), now_ms)


def from_ear(slug: str, confidence: float, now_ms: int | None = None) -> None:
    now = _now(now_ms)
    _send({"kind": "speaker", "person": slug, "permille": _permille(confidence), "at_ms": now}, now)


def from_people(slugs: list, now_ms: int | None = None) -> None:
    now = _now(now_ms)
    _send({"kind": "presence", "people": list(slugs), "at_ms": now}, now)


def from_vision(scene_ref: str, now_ms: int | None = None) -> None:
    now = _now(now_ms)
    _send({"kind": "scene", "reference": scene_ref, "at_ms": now}, now)


def from_mood(slug: str, valence: float, arousal: float, source: str = "umore", now_ms: int | None = None) -> None:
    now = _now(now_ms)
    _send({"kind": "emotion", "person": slug, "valence": max(-1000, min(1000, round(valence * 1000))),
           "arousal": max(0, min(1000, round(arousal * 1000))), "source": source, "at_ms": now}, now)


MOOD_AXES = {"felice": (0.8, 0.6), "sereno": (0.5, 0.2), "entusiasta": (0.9, 0.9), "innamorato": (0.9, 0.7), "grato": (0.7, 0.4),
             "neutro": (0.0, 0.3), "stanco": (-0.3, 0.1), "annoiato": (-0.3, 0.2), "stressato": (-0.6, 0.8),
             "preoccupato": (-0.5, 0.6), "triste": (-0.8, 0.2), "arrabbiato": (-0.7, 0.9), "malato": (-0.6, 0.2)}


def _guarded(call, *args) -> None:
    if not enabled():
        return
    try:
        call(*args)
    except (OSError, ValueError, RuntimeError) as exc:
        log.error("Osservazione scartata dalla percezione: %s", exc)


def note_speaker(slug: str, confidence: float) -> None:
    _guarded(from_ear, slug, confidence)


def note_people(slugs: list) -> None:
    _guarded(from_people, [s for s in slugs if s])


def note_scene(ref: str | None) -> None:
    if ref:
        _guarded(from_vision, ref)


def note_mood(slug: str, mood: str, intensity: int, source: str) -> None:
    axes = MOOD_AXES.get(mood)
    if axes is None:
        return
    scale = max(1, min(5, int(intensity))) / 5
    _guarded(from_mood, slug, axes[0] * scale, axes[1] * scale, source)


def context_for(text: str, present: list, speaker: str = "", channel: str = "text", lang: str = "it") -> str:
    if not enabled():
        return hot.context_for(present, lang=lang)
    try:
        now = _now(None)
        from_people(present, now)
        if speaker:
            from_ear(speaker, 1.0, now)
        request = {"id": f"p{uuid.uuid4().hex}", "channel": channel, "text": text, "lang": lang, "budget_chars": 0}
        return json.loads(_fusion().fuse(json.dumps(request), now))["view"]
    except (OSError, ValueError, RuntimeError) as exc:
        log.error("Fusione del percetto non riuscita: %s", exc)
        return hot.context_for(present, lang=lang)


def reset() -> None:
    with _lock:
        _state.update(ctx=None, fusion=None)
