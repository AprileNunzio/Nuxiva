import json
import logging
import os
import threading
import time
from datetime import date

from agenti.people import people

log = logging.getLogger("nuxiva.people.hot")
KEYS = (
    "slug", "first_name", "last_name", "name", "nickname", "role", "consent", "share_health", "occupation",
    "languages", "relations", "food_likes", "food_dislikes", "drinks", "coffee", "music", "movies", "sports",
    "hobbies", "custom", "allergies", "intolerances", "diet", "notes",
)
_lock = threading.Lock()
_state = {"ctx": None, "day": None, "today": {}}


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustUserContext", None)


def enabled() -> bool:
    return os.environ.get("NUXIVA_CONTEXT_ENGINE", "rust") == "rust" and _native() is not None


def _latest_mood(profile: dict) -> dict | None:
    rows = [e for e in profile.get("mood_journal") or [] if isinstance(e, dict) and e.get("mood")]
    return max(rows, key=lambda e: float(e.get("at") or 0), default=None)


def enrich(profile: dict, today: dict) -> dict:
    out = {k: profile[k] for k in KEYS if k in profile}
    out["age"] = people.age(profile)
    if profile.get("sessions"):
        out["habits_summary"] = people.habits(profile)["summary"]
    out["today"] = today.get(profile.get("slug"), [])
    out["mood"] = _latest_mood(profile)
    return out


def _today_map() -> dict:
    mapping: dict = {}
    for row in people.reminders(days=0):
        mapping.setdefault(row["slug"], []).append(row["title"])
    return mapping


def _reload() -> None:
    today = _today_map()
    profiles = [p for p in people.all_profiles(light=True) if not p.get("deceased")]
    ctx = _native()()
    result = json.loads(ctx.load_profiles(json.dumps([enrich(p, today) for p in profiles])))
    if result["rejected"]:
        log.warning("Profili non caricati nella memoria calda: %s", result["rejected"])
    _state.update(ctx=ctx, day=date.today(), today=today)


def _ready():
    with _lock:
        if _state["ctx"] is None or _state["day"] != date.today():
            _reload()
        return _state["ctx"]


def refresh(slug: str) -> None:
    if _state["ctx"] is None or not enabled():
        return
    try:
        profile = people.load(slug)
        if profile is None or profile.get("deceased"):
            _state["ctx"].remove(people.slugify(slug))
        else:
            _state["ctx"].upsert_profile(json.dumps(enrich(profile, _state["today"])))
    except (OSError, ValueError, RuntimeError) as exc:
        log.error("Aggiornamento della memoria calda non riuscito per %s: %s", slug, exc)


def forget(slug: str) -> None:
    if _state["ctx"] is None or not enabled():
        return
    try:
        _state["ctx"].remove(people.slugify(slug))
    except ValueError as exc:
        log.error("Rimozione dalla memoria calda non riuscita per %s: %s", slug, exc)


def context_for(present: list, subjects: list | None = None, lang: str = "it") -> str:
    if not enabled():
        return people.context_for(present)
    try:
        ctx = _ready()
        now_ms = int(time.time() * 1000)
        ctx.set_presence(list(present), now_ms)
        return ctx.render(list(subjects if subjects is not None else present), list(present), lang, 0, now_ms)
    except (OSError, ValueError, RuntimeError) as exc:
        log.error("Memoria calda non disponibile: %s", exc)
        return ""


def reset() -> None:
    with _lock:
        _state.update(ctx=None, day=None, today={})
