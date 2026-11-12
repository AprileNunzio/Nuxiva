import math
import re

ATTEMPT = 60.0
RETRY_FIRST = 20.0
RETRY_MAX = 300.0
SHOW = 45.0
REFRESH = 15 * 60.0
AWAY_GRACE = 8.0
FORGET_AFTER = 30 * 60.0
MAX_PEOPLE = 4
MAX_TRACKED = 64
MAX_SEEN = 32
LIMITS = {"heart_rate": (40, 180), "resp_rate": (5, 40)}
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def clean(values) -> dict:
    out = {}
    if not isinstance(values, dict):
        return out
    for metric, (low, high) in LIMITS.items():
        value = values.get(metric)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high:
            out[metric] = float(round(value))
    return out


def _gap(tries: int) -> float:
    return min(RETRY_MAX, RETRY_FIRST * (2 ** min(max(tries - 1, 0), 8)))


class PyWatch:

    def __init__(self) -> None:
        self._people: dict[str, dict] = {}

    @staticmethod
    def _new(now: float, last_seen: float | None = None) -> dict:
        return {"state": "idle", "since": now, "tries": 0, "values": {}, "source": "", "got_at": 0.0,
                "last_seen": now if last_seen is None else last_seen}

    @staticmethod
    def _show(person: dict, values: dict, source: str, now: float) -> None:
        if person["state"] != "shown":
            person.update(state="shown", since=now, tries=0, values={})
        person["values"].update(values)
        person["source"], person["got_at"] = source, now

    def _step(self, slug: str, person: dict, seen: dict, camera_on: bool, now: float, force: list) -> None:
        state = person["state"]
        if state == "shown" and now - person["since"] >= SHOW:
            force.append((slug, 0.0))
            person["state"], person["since"] = "cooldown", now
            return
        if state != "cooldown" and "heart_rate" in seen["device"]:
            if state == "attempt":
                force.append((slug, 0.0))
            self._show(person, seen["device"], "device", now)
            return
        if state == "idle":
            person["state"], person["since"] = "attempt", now
            if camera_on:
                force.append((slug, ATTEMPT))
        elif state == "attempt":
            if "heart_rate" in seen["camera"]:
                self._show(person, seen["camera"], "camera", now)
            elif now - person["since"] >= ATTEMPT or not camera_on:
                force.append((slug, 0.0))
                person["tries"] += 1
                person["state"], person["since"] = "rest", now
        elif state == "rest" and now - person["since"] >= _gap(person["tries"]):
            person["state"], person["since"] = "attempt", now
            if camera_on:
                force.append((slug, ATTEMPT))
        elif state == "shown" and person["source"] == "camera" and seen["camera"]:
            self._show(person, seen["camera"], "camera", now)
        elif state == "cooldown" and now - person["since"] >= REFRESH:
            person.update(self._new(now, person["last_seen"]))

    def _leave(self, slug: str, person: dict, now: float, force: list) -> None:
        if person["state"] in ("attempt", "shown"):
            force.append((slug, 0.0))
        if person["state"] == "shown":
            person["state"], person["since"] = "cooldown", now
        elif person["state"] != "cooldown":
            person.update(self._new(now, person["last_seen"]))

    def tick(self, seen: list, camera_on: bool, now: float) -> tuple[list[dict], list[tuple[str, float]]]:
        force: list[tuple[str, float]] = []
        present: list[dict] = []
        if not math.isfinite(now):
            return [], force
        for item in seen[:MAX_SEEN]:
            slug = item.get("slug") if isinstance(item, dict) else None
            if len(present) >= MAX_PEOPLE:
                break
            if isinstance(slug, str) and SLUG.match(slug) and all(p["slug"] != slug for p in present):
                present.append({"slug": slug, "device": clean(item.get("device")), "camera": clean(item.get("camera"))})
        for item in present:
            slug = item["slug"]
            if slug not in self._people and len(self._people) >= MAX_TRACKED:
                continue
            person = self._people.setdefault(slug, self._new(now))
            person["last_seen"] = now
            self._step(slug, person, item, camera_on, now, force)
        slugs = {p["slug"] for p in present}
        for slug, person in sorted(self._people.items()):
            if slug in slugs:
                continue
            away = now - person["last_seen"]
            if away > FORGET_AFTER:
                force.append((slug, 0.0))
                del self._people[slug]
            elif away > AWAY_GRACE:
                self._leave(slug, person, now, force)
        shown = [{"slug": p["slug"], "values": dict(self._people[p["slug"]]["values"]), "source": self._people[p["slug"]]["source"],
                  "at": round(self._people[p["slug"]]["got_at"], 1)}
                 for p in present if p["slug"] in self._people and self._people[p["slug"]]["state"] == "shown"]
        return shown, force

    def forget(self, slug: str) -> bool:
        return self._people.pop(slug, None) is not None

    def tracked(self) -> int:
        return len(self._people)
