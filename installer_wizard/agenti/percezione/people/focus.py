import time

from agenti.people import mood, people, sync_view
from agenti.people.panel import focus_of, initials, series, visible_people
from agenti.medico.vitals import cloud, service
from agenti.medico.vitals.checkup import checkup
from state import store
from tasks import background

CLOUD_EVERY = 120.0
_polled: dict[str, float] = {}


def _away() -> bool:
    privacy = getattr(store, "privacy", None)
    return bool(isinstance(privacy, dict) and privacy.get("away"))


def _who(slug: str) -> dict | None:
    profile = people.load(slug) if slug else None
    if not profile:
        return None
    name = people.display_name(profile)
    return {"slug": slug, "name": name, "initials": initials(name)}


def _focus() -> str:
    return "" if _away() else focus_of("", visible_people())


def _kick(slug: str, now: float) -> None:
    if cloud.ready(slug) and now - _polled.get(slug, 0.0) >= CLOUD_EVERY:
        _polled[slug] = now
        background(cloud.poll(slug, now))


def health_card() -> dict | None:
    slug = _focus()
    who = _who(slug)
    if not who:
        return None
    now = time.time()
    _kick(slug, now)
    view = service.health_view(slug, now)
    if not view:
        return None
    view.pop("at", None)
    return {"person": who, **view}


def mood_card() -> dict | None:
    slug = _focus()
    who = _who(slug)
    if not who:
        return None
    now = time.time()
    latest = mood.latest(slug)
    entry = None
    if latest and latest.get("feedback") != "wrong":
        entry = {"mood": latest["mood"], "intensity": latest["intensity"], "source": latest["source"], "at": latest["at"],
                 "evidence": latest.get("evidence", "")}
    face = None
    try:
        from agenti.medico.wellbeing import service as wellbeing
        signal = wellbeing.live(slug, now)
        if signal and not signal.get("calibrating"):
            face = {"area": signal["area"], "arousal": signal["arousal"], "valence": signal["valence"]}
    except (ImportError, KeyError, TypeError, ValueError):
        face = None
    if not entry and not face:
        return None
    return {"person": who, "mood": entry, "face": face, "week": series(slug, now)}


def sync_card() -> dict | None:
    slug = _focus()
    who = _who(slug)
    if not who:
        return None
    now = time.time()
    _kick(slug, now)
    view = sync_view.build(slug, now)
    return {"person": who, **view} if view else None


def checkup_card() -> dict | None:
    if _away():
        return None
    rows = []
    for reading in checkup.tick(visible_people(), time.time()):
        who = _who(reading["slug"])
        if who:
            rows.append({"person": who, "values": reading["values"], "source": reading["source"], "at": reading["at"]})
    return {"people": rows} if rows else None
