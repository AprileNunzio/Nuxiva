import re

from features.music import catalog as library, layout, lyrics as online
from features.music.db import db
from features.musicstudio import schema as S

REFERENCE = re.compile(r"\b(?:di|del|della|dei|by|from)\s+(?P<ref>[^,.;]+?)(?=\s+(?:in\s+versione|versione|in\s+(?:inglese|francese|spagnolo|tedesco|portoghese|italiano)|con|stile|per)\b|[,.;]|$)", re.I)
TOKEN = re.compile(r"[a-z0-9à-ÿ']{2,}")
TIME = re.compile(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")


def reference(prompt: str) -> str:
    found = [m.group("ref").strip() for m in REFERENCE.finditer(prompt or "")]
    return S.text(found[-1], 80) if found else ""


def _words(text: str) -> set[str]:
    return set(TOKEN.findall(text.lower()))


def match(ref: str) -> dict | None:
    wanted = _words(ref)
    if not wanted:
        return None
    for row in library.search(ref, 12)["tracks"]:
        if wanted <= _words(f"{row['title']} {row['artist']} {row['album']}"):
            return row
    return None


def _sidecar(track_id: int) -> str:
    row = db.row("SELECT path FROM tracks WHERE id=?", (track_id,))
    if not row:
        return ""
    path = (layout.root() / row["path"]).with_suffix(".lrc")
    try:
        raw = path.read_text(encoding="utf-8")[:20000]
    except OSError:
        return ""
    return "\n".join(line for line in (TIME.sub("", l).strip() for l in raw.splitlines()) if line)


async def lyrics_of(track: dict) -> str:
    text = _sidecar(int(track["id"]))
    if text:
        return S.text(text, 2400, True)
    data = await online.fetch(track["title"], track["artist"], track.get("album") or "", track.get("duration"))
    if data.get("synced"):
        return S.text("\n".join(l["text"] for l in data["synced"] if l["text"]), 2400, True)
    return S.text(data.get("plain"), 2400, True)


async def find(prompt: str) -> dict | None:
    ref = reference(prompt)
    track = match(ref) if ref else None
    if track is None:
        return None
    text = await lyrics_of(track)
    return {"id": int(track["id"]), "title": track["title"], "artist": track["artist"], "text": text} if text else None
