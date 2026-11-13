import asyncio
import logging
import time

from config import write_env
from state import store

from agenti.music import catalog, conf, layout, lyrics

log = logging.getLogger("nuxiva.music")
ENV = "NUXIVA_MUSIC_KARAOKE"
WIDGET = "karaoke"
KEEP = 24
MAX_TEXT = 8000
loaded: dict = {}
pending: set = set()


def enabled() -> bool:
    return conf.flag(ENV, False)


def set_enabled(on: bool) -> bool:
    write_env({ENV: "1" if on else "0"})
    from agenti.desktop.desk import desk
    if on:
        desk.suppressed.discard(f"bind:{WIDGET}")
        desk.dismissed.pop(f"bind:{WIDGET}", None)
    else:
        desk.hide(key=f"bind:{WIDGET}")
    store.event("INFO", f"Abilità karaoke {'attivata' if on else 'disattivata'}", "music")
    return on


def song_id(np_: dict) -> str:
    return "|".join(str(np_.get(k) or "") for k in ("key", "title", "artist"))


def local_text(np_: dict) -> str:
    key = str(np_.get("key") or "")
    if not key.startswith("lib:") or not key[4:].isdigit():
        return ""
    row = catalog.track(int(key[4:]))
    if not row:
        return ""
    try:
        return (layout.root() / row["path"]).with_suffix(".lrc").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def shaped(raw: str) -> dict:
    synced = lyrics._parse(raw)
    if synced:
        return {"synced": synced}
    plain = raw.strip()[:MAX_TEXT]
    return {"plain": plain} if plain else {}


def remember(ident: str, found: dict, origin: str = "") -> None:
    loaded[ident] = {"data": found, "origin": origin, "at": time.time()}
    while len(loaded) > KEEP:
        loaded.pop(next(iter(loaded)))


async def resolve(np_: dict) -> None:
    ident = song_id(np_)
    try:
        raw = await asyncio.to_thread(local_text, np_)
        found = shaped(raw) if raw else {}
        origin = "local" if found else ""
        if not found and conf.lyrics_online():
            found = await lyrics.fetch(str(np_.get("title") or ""), str(np_.get("artist") or ""), str(np_.get("album") or ""), np_.get("duration") or None)
            origin = "lrclib" if found else ""
        remember(ident, found or {}, origin)
    except Exception as exc:
        log.warning("Testo del karaoke non caricato: %s", exc)
        remember(ident, {})
    finally:
        pending.discard(ident)
        store.touch()


def ensure(np_: dict) -> tuple[dict | None, str]:
    ident = song_id(np_)
    if np_.get("lyrics"):
        return np_["lyrics"], "local" if str(np_.get("key") or "").startswith("lib:") else "lrclib"
    hit = loaded.get(ident)
    if hit is not None:
        return hit["data"], hit["origin"]
    if ident not in pending:
        try:
            asyncio.get_running_loop().create_task(resolve(np_))
            pending.add(ident)
        except RuntimeError:
            return None, ""
    return None, ""


def source() -> dict:
    if not enabled():
        return {}
    from agenti.music import music
    np_ = music.watcher.current()
    if not np_ or not np_.get("title"):
        return {}
    found, origin = ensure(np_)
    state = "loading" if found is None else "ready" if found else "none"
    return {**{k: np_.get(k) for k in ("key", "title", "artist", "album", "cover", "duration", "started_at") if np_.get(k) is not None},
            "lyrics": found or {}, "lyrics_state": state, "lyrics_origin": origin}
