import asyncio
import io
import logging
import random
import re
import time
import wave

from features.brain.llm import BrainUnavailable
from tasks import background

from features.tasks.registry import registry as board

from features.voices import languages
from features.musicstudio import composer, songtext, generator, lyrics as lyr, schema as S, store

log = logging.getLogger("nuxiva.musicstudio")
FAILURES = (BrainUnavailable, ValueError, KeyError, TypeError, AttributeError, asyncio.TimeoutError)
jobs: dict[str, dict] = {}
ASSET_RE = re.compile(r"^[0-9a-f]{8}\.wav$")


def status(pid: str) -> dict:
    return dict(jobs.get(pid) or {"state": "idle", "stage": ""})


PROGRESS = {"plan": 0.1, "lyrics": 0.3, "translate": 0.45, "voices": 0.6, "render": 0.85}
LABELS = {"plan": "Arrangiamento: genere, tonalità, strumenti", "lyrics": "Testo della canzone", "translate": "Traduzione del testo", "voices": "Registrazione delle voci", "render": "Mix e file audio"}


def _steps(current: str) -> list[dict]:
    order = list(PROGRESS)
    index = order.index(current)
    return [{"text": LABELS[k], "state": "done" if i < index else "running" if i == index else "pending"} for i, k in enumerate(order)]


def _set(pid: str, **changes) -> None:
    jobs[pid] = {**jobs.get(pid, {"state": "idle", "stage": ""}), **changes}
    task = jobs[pid].get("task")
    if task and changes.get("stage") in PROGRESS:
        board.update(task, progress=PROGRESS[changes["stage"]], stage=changes["stage"], steps=_steps(changes["stage"]))


def create(prompt: str) -> dict:
    clean = S.text(prompt, 600)
    if len(clean) < 3:
        raise S.SpecError("prompt_short")
    if len(store.ids()) >= store.MAX_PROJECTS:
        raise S.SpecError("library_full")
    spec = composer.heuristic(clean)
    project = generator.arrange({**spec, "seed": random.SystemRandom().randrange(1 << 30)})
    store.save(project)
    task = board.start("song", clean[:80], "musicstudio", project["id"], clean)
    _set(project["id"], state="building", stage="plan", task=task)
    background(_enrich(project["id"], clean))
    return project


async def _enrich(pid: str, prompt: str) -> None:
    task = jobs.get(pid, {}).get("task", "")
    try:
        await _compose(pid, prompt)
        if board.is_cancelled(task):
            _set(pid, state="error", stage="", error="cancelled")
            return
        await _deliver(pid, task)
    except asyncio.CancelledError:
        board.fail(task, "cancelled")
        raise
    except Exception as exc:
        log.exception("musicstudio %s: creation failed", pid)
        _set(pid, state="error", stage="", error="failed")
        board.fail(task, type(exc).__name__)


async def _deliver(pid: str, task: str) -> None:
    from features.musicstudio import exporter, renderer
    _set(pid, stage="render")
    project = store.load(pid)
    board.update(task, title=project["title"] or project["prompt"][:80])
    wav = await asyncio.to_thread(renderer.render, project)
    try:
        shelf = await asyncio.to_thread(exporter.save, project, wav)
    except OSError:
        shelf = {"folder": "", "library": ""}
    _set(pid, state="done", stage="", published=shelf.get("library", ""))
    title = project["title"] or project["prompt"] or "Canzone"
    try:
        from features.desktop.desk import desk
        desk.show("notice", {"title": "Studio Musicale", "text": f"«{title}» è pronta. Vuoi ascoltarla, aprire lo Studio o parlarne?"}, ttl=180)
    except (ImportError, AttributeError, OSError):
        pass
    board.finish(task, f"«{title}» è pronta" + (" e la trovi nel Media Player." if shelf.get("library") else "."),
                 {"app": "musicstudio", "payload": {"project": pid}, "file": shelf.get("library", "")},
                 {"question": f"«{title}» è pronta. Vuoi ascoltarla, aprire lo Studio o parlarne con me?",
                  "actions": [{"id": "listen", "label": "listen"}, {"id": "open", "label": "open"}, {"id": "talk", "label": "talk"}]})


async def _compose(pid: str, prompt: str) -> None:
    try:
        try:
            spec = await composer.plan(prompt)
            project = generator.arrange({**spec, "seed": random.SystemRandom().randrange(1 << 30)})
            project = S.clean_project({**project, "id": pid, "created": store.load(pid)["created"]}, pid)
        except FAILURES as exc:
            log.info("musicstudio %s: plan fallback (%s)", pid, type(exc).__name__)
            spec = composer.heuristic(prompt)
            project = store.load(pid)
        store.save(project)
        _set(pid, stage="lyrics")
        text = spec.get("lyrics") or ""
        borrowed = None
        if spec.get("vocals") and spec.get("reference"):
            borrowed = await _library_song(prompt)
            if borrowed:
                text = ""
                _set(pid, notice="lyrics_from_library" if borrowed.get("source") == "library" else "lyrics_from_web")
            else:
                _set(pid, notice="lyrics_not_found")
                spec = {**spec, "vocals": False}
        if borrowed:
            project["lyrics"] = S.clean_lyrics({"lang": languages.detect(borrowed["text"], "it"), "text": borrowed["text"]})
            project["revision"] += 1
            store.save(project)
            _set(pid, stage="translate")
            try:
                await translate(pid, spec.get("lang", "it"), True)
            except (S.SpecError, *FAILURES):
                _set(pid, notice="translation_failed")
            return
        if spec.get("vocals") and not text:
            try:
                text = await lyr.write(prompt, project["genre"], spec.get("lang", "it"), spec.get("mood", ""))
            except FAILURES:
                text = ""
        if spec.get("vocals") and text:
            project["lyrics"] = S.clean_lyrics({"lang": spec.get("lang", "it"), "text": text})
            project["tracks"].append(generator.vocal_track(project, text, spec.get("lang", "it")))
            project["revision"] += 1
            store.save(project)
            _set(pid, stage="voices")
            await voice_assets(pid)
    except KeyError:
        _set(pid, state="error", stage="", error="missing")
        raise
    except OSError:
        _set(pid, state="error", stage="", error="storage")
        raise


async def _library_song(prompt: str) -> dict | None:
    try:
        return await songtext.find(prompt)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def wav_seconds(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data), "rb") as clip:
            return clip.getnframes() / float(clip.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return 0.0


async def sing(vocal: dict, slot: float) -> bytes:
    from features.voices import synthesis
    speed = vocal["speed"]
    voice = vocal["voice"] or None
    wav = await synthesis.synthesize(vocal["text"], voice, speed, vocal["lang"], vocal["pitch"] or None)
    length = wav_seconds(wav)
    if slot > 0 and length > slot:
        faster = min(1.6, speed * length / slot * 1.02)
        if faster > speed + 0.04:
            wav = await synthesis.synthesize(vocal["text"], voice, faster, vocal["lang"], vocal["pitch"] or None)
            vocal["speed"] = round(faster, 3)
    return wav


async def voice_assets(pid: str) -> int:
    project = store.load(pid)
    made = 0
    seconds_per_beat = 60.0 / project["tempo"]
    for track in project["tracks"]:
        for clip in track["clips"]:
            vocal = clip.get("vocal")
            if not vocal or not vocal["text"] or vocal["asset"]:
                continue
            try:
                wav = await sing(vocal, clip["length"] * seconds_per_beat)
            except (ValueError, RuntimeError, asyncio.TimeoutError, OSError) as exc:
                log.info("musicstudio %s: voice skipped (%s)", pid, type(exc).__name__)
                continue
            name = f"{S.new_id()}.wav"
            (store.audio_dir(pid) / name).write_bytes(wav)
            vocal["asset"] = name
            made += 1
    if made:
        project["revision"] += 1
        store.save(project)
    return made


def add_layer(pid: str, role: str, instrument: str = "") -> dict:
    project = store.load(pid)
    track = generator.add_layer(project, role, instrument)
    project["tracks"].append(track)
    project["revision"] += 1
    store.save(project)
    return project


async def add_vocals(pid: str, text: str, lang: str, voice: str = "") -> dict:
    project = store.load(pid)
    body = S.text(text, 2400, True) or project["lyrics"]["text"]
    if not body:
        raise S.SpecError("lyrics_empty")
    if len(project["tracks"]) >= S.MAX_TRACKS:
        raise S.SpecError("tracks_full")
    project["lyrics"] = S.clean_lyrics({**project["lyrics"], "lang": lang, "text": body, "translations": project["lyrics"]["translations"]})
    track = generator.vocal_track(project, body, lang, voice)
    if not track["clips"]:
        raise S.SpecError("no_sections")
    project["tracks"].append(track)
    project["revision"] += 1
    store.save(project)
    await voice_assets(pid)
    return store.load(pid)


async def translate(pid: str, lang: str, sing: bool = True, voice: str = "") -> dict:
    project = store.load(pid)
    source = project["lyrics"]["text"]
    if not source:
        raise S.SpecError("lyrics_empty")
    translated = await lyr.translate(source, lang)
    if not translated:
        raise ValueError("translation_empty")
    project["lyrics"]["translations"][lang] = translated
    project["revision"] += 1
    store.save(project)
    if sing and len(project["tracks"]) < S.MAX_TRACKS:
        track = generator.vocal_track(project, translated, lang, voice)
        track["name"] = f"Voce ({lang.upper()})"
        project["tracks"].append(track)
        project["revision"] += 1
        store.save(project)
        await voice_assets(pid)
    return store.load(pid)


def asset_path(pid: str, name: str):
    if not ASSET_RE.fullmatch(name):
        raise KeyError(name)
    path = store.audio_dir(pid) / name
    if not path.is_file():
        raise KeyError(name)
    return path


def touch(project: dict) -> dict:
    project["revision"] += 1
    project["created"] = project["created"] or int(time.time())
    return project


def add_effect(pid: str, kind: str, role: str = "") -> dict:
    from features.musicstudio import catalog as C
    if kind not in C.EFFECT_BY_ID:
        raise S.SpecError("effect_invalid")
    project = store.load(pid)
    fresh = S.clean_effect({"type": kind, "params": {}})
    targets = [t for t in project["tracks"] if t["role"] == role] if role else []
    if targets:
        for track in targets:
            if len(track["effects"]) < S.MAX_EFFECTS and all(e["type"] != kind for e in track["effects"]):
                track["effects"].append({**fresh, "id": S.new_id()})
    elif len(project["master"]["effects"]) < S.MAX_EFFECTS:
        project["master"]["effects"].append(fresh)
    project["revision"] += 1
    store.save(project)
    return project


def set_tempo(pid: str, tempo: float) -> dict:
    project = store.load(pid)
    project["tempo"] = S.number(tempo, 40, 220, project["tempo"])
    project["revision"] += 1
    store.save(project)
    return project


async def revoice(pid: str, track_id: str, voice: str, speed: float | None = None) -> dict:
    project = store.load(pid)
    track = next((t for t in project["tracks"] if t["id"] == track_id), None)
    if track is None:
        raise KeyError(track_id)
    changed = 0
    for clip in track["clips"]:
        vocal = clip.get("vocal")
        if vocal and vocal["text"]:
            vocal.update(voice=S.text(voice, 40), asset="")
            if speed is not None:
                vocal["speed"] = S.number(speed, 0.6, 1.6, vocal["speed"])
            changed += 1
    if not changed:
        raise S.SpecError("no_sections")
    project["revision"] += 1
    store.save(project)
    await voice_assets(pid)
    return store.load(pid)
