import json
import re
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

from tasks import background

from agenti.hands.holo import exact, hd
from agenti.hands.holo.session import FINAL, MODES, session

LANGS = ("it", "en", "fr", "es")
MAX_WORDS = 12
FOLDER = Path(__file__).resolve().parent / "language"


@lru_cache(maxsize=len(LANGS))
def vocab(lang: str) -> dict:
    code = lang if lang in LANGS else "it"
    return json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))


def _code(lang: str) -> str:
    code = str(lang or "it")[:2].lower()
    return code if code in LANGS else "it"


def norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", plain).strip() + " "


@lru_cache(maxsize=len(LANGS))
def _phrases(lang: str) -> tuple[tuple[str, str], ...]:
    pairs = ((norm(phrase), name) for name, phrases in vocab(lang)["commands"].items() for phrase in phrases)
    return tuple(sorted(pairs, key=lambda pair: -len(pair[0])))


def match(text: str, lang: str, names: tuple[str, ...] | None = None) -> str | None:
    padded = norm(text)
    for phrase, name in _phrases(_code(lang)):
        if (names is None or name in names) and phrase in padded:
            return name
    return None


def initial_mode(text: str, lang: str) -> str:
    return match(text, lang, ("anatomy", "realistic")) or "particles"


def say(lang: str, key: str, **values) -> str:
    return vocab(_code(lang))["replies"][key].format(**values)


def _launch(subject: str, mode: str, spec: dict | None, lang: str) -> dict:
    session_id = session.begin(subject, mode)
    kind = exact.kind_of(subject)
    if kind is None:
        background(hd.build(session_id, subject, spec, _code(lang)))
        return session.brief()
    scene = exact.scene(kind, _code(lang))
    session.scene_ready(session_id, scene, "exact")
    _show_particles(subject, exact.to_particles(scene))
    return session.brief()


def _show_particles(subject: str, spec: dict) -> None:
    from agenti.particles import codec, show as particles_show
    from agenti.particles.store import store
    seed = int.from_bytes(subject.encode()[:8].ljust(8, b"\0"), "little")
    entry = store.put(subject, spec, codec.sample(spec, particles_show.POINTS, seed))
    particles_show.present(entry, query=subject)


def follow(visual: dict, text: str, lang: str) -> dict:
    from agenti.particles.store import store
    ui = visual.get("ui") if isinstance(visual.get("ui"), dict) else {}
    subject = str((ui.get("particles") or {}).get("concept") or "")
    if not subject:
        return visual
    hit = store.lookup(subject) or {}
    ui["holo"] = _launch(subject, initial_mode(text, lang), hit.get("spec"), lang)
    from agenti.particles import show as particles_show
    ui["particles"] = particles_show.current() or ui.get("particles")
    visual["ui"] = ui
    return visual


def start(subject: str, mode: str, lang: str) -> dict:
    from agenti.particles import show as particles_show
    entry = particles_show.materialize_instant(subject)
    shown = particles_show.present(entry, query=subject)
    if entry.get("instant") and exact.kind_of(subject) is None:
        particles_show.refine_later(subject, subject)
    holo = _launch(shown["concept"], mode, entry.get("spec"), lang)
    return {"particles": particles_show.current(), "holo": holo}


def _mode_reply(name: str, snap: dict, lang: str) -> str:
    subject = snap["subject"]
    if name == "particles":
        from agenti.particles import show as particles_show
        particles_show.present(particles_show.materialize_instant(subject), query=subject)
        return say(lang, "particles", subject=subject)
    if snap["status"] == "failed":
        return say(lang, "unavailable", reason=snap["reason"] or "-")
    if name == "realistic" and snap["source"] not in FINAL:
        return say(lang, "realistic_wait", subject=subject)
    return say(lang, name, subject=subject)


async def answer(text: str, lang: str = "it") -> dict | None:
    if not session.active() or len(str(text or "").split()) > MAX_WORDS:
        return None
    from agenti.particles import morphogenesis
    if morphogenesis.extract_visual_concept(text or ""):
        return None
    name = match(text, lang)
    if name is None:
        return None
    started = time.monotonic()
    snap = session.snapshot()
    if name == "close":
        from agenti.particles import show as particles_show
        session.close()
        particles_show.clear()
        reply = say(lang, "close")
    elif name in MODES:
        session.set_mode(name)
        reply = _mode_reply(name, snap, lang)
    else:
        session.command(name)
        reply = say(lang, "view")
    return {"reply": reply, "ui": {"mode": "face", "holo": session.brief()}, "intent": "holo", "agent": "ologramma",
            "elapsed_ms": int((time.monotonic() - started) * 1000)}
