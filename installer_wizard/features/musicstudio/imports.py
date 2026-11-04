import asyncio
import shutil
import subprocess
import wave
from pathlib import Path

from features.music import layout
from features.musicstudio import schema as S, store
from features.shares import archive

KINDS = ("musica", "scambio", "produzioni")
MAX_SOURCE = 80 * 1024 * 1024
MAX_SECONDS = 420
MAX_LISTED = 200
TIMEOUT = 180
AUDIO = layout.AUDIO | {".wav"}


def _root(kind: str) -> Path:
    if kind not in KINDS:
        raise S.SpecError("source_invalid")
    return archive.folder(kind).resolve()


def browse(kind: str) -> list[dict]:
    root = _root(kind)
    rows = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO and not path.name.startswith(".") and "Cestino" not in path.parts:
            stat = path.stat()
            rows.append((stat.st_mtime, {"path": path.relative_to(root).as_posix(), "name": path.stem, "size": stat.st_size}))
    rows.sort(key=lambda r: r[0], reverse=True)
    return [r[1] for r in rows[:MAX_LISTED]]


def resolve(kind: str, relative: str) -> Path:
    root = _root(kind)
    path = (root / str(relative or "")).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in AUDIO or path.stat().st_size > MAX_SOURCE:
        raise S.SpecError("source_invalid")
    return path


def convert(source: Path, target: Path) -> float:
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise S.SpecError("converter_missing")
    argv = [binary, "-nostdin", "-loglevel", "error", "-y", "-i", str(source), "-t", str(MAX_SECONDS), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(target)]
    try:
        subprocess.run(argv, check=True, capture_output=True, timeout=TIMEOUT)
        with wave.open(str(target), "rb") as clip:
            return clip.getnframes() / float(clip.getframerate())
    except (OSError, subprocess.SubprocessError, wave.Error, EOFError) as exc:
        target.unlink(missing_ok=True)
        raise S.SpecError("source_unreadable") from exc


async def bring(pid: str, kind: str, relative: str) -> dict:
    project = store.load(pid)
    if len(project["tracks"]) >= S.MAX_TRACKS:
        raise S.SpecError("tracks_full")
    source = resolve(kind, relative)
    name = f"{S.new_id()}.wav"
    target = store.audio_dir(pid) / name
    seconds = await asyncio.to_thread(convert, source, target)
    beats = max(0.25, min(S.MAX_BARS * 8, seconds * project["tempo"] / 60))
    clip = {"id": S.new_id(), "name": S.text(source.stem, 40), "start": 0, "length": beats, "notes": [],
            "vocal": {"text": "", "lang": "it", "voice": "", "speed": 1, "pitch": 0, "asset": name}}
    track = S.clean_track({"role": "vocal", "name": S.text(source.stem, 40), "clips": [clip]})
    project["tracks"].append(track)
    project["revision"] += 1
    store.save(project)
    return project
