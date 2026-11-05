import threading
import time
from datetime import date

from features.sentinel import record

SHUTTER = {"guest_only": "sentinel.word.guest_only", "mixed": "sentinel.word.mixed"}
COLORS = frozenset({"black", "white", "grey", "red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink",
                    "brown"})


def display_name(slug: str) -> str:
    from features.people import people
    return str((people.load(slug) or {}).get("name") or slug)[:60]


class PresenceCollector:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.members: set[str] = set()
        self.kind: str | None = None
        self.guests: list[int] = []
        self.issued = 0
        self.day = date.today()
        self.attire: dict[str, str] = {}

    def _color(self, slug: str) -> str | None:
        color = self.attire.get(slug)
        return f"sentinel.color.{color}" if color in COLORS and record.option("NUXIVA_SENTINEL_APPEARANCE") else None

    def _person(self, slug: str, arrived: bool, at: float) -> None:
        color = self._color(slug)
        base = "sentinel.presence.arrived" if arrived else "sentinel.presence.left"
        params = {"person": display_name(slug)}
        if color:
            params["color"] = color
        record.record("presence.arrived" if arrived else "presence.left", record.person(slug),
                      base + ("_wearing" if color else ""), params, "personal", "presence", at=at)

    def _guests(self, count: int, at: float) -> None:
        if not record.option("NUXIVA_SENTINEL_GUESTS"):
            self.guests = list(range(1, count + 1))
            return
        while len(self.guests) < count:
            self.issued += 1
            self.guests.append(self.issued)
            record.record("guest.arrived", record.guest(self.issued), "sentinel.guest.arrived",
                          {"guest": self.issued}, "household", "presence", at=at)
        while len(self.guests) > count:
            number = self.guests.pop()
            record.record("guest.left", record.guest(number), "sentinel.guest.left", {"guest": number},
                          "household", "presence", at=at)

    def update(self, audience: dict, people: list, at: float | None = None) -> None:
        if not record.enabled():
            return
        at = at or time.time()
        with self._lock:
            today = date.fromtimestamp(at)
            if today != self.day:
                self.day, self.issued, self.guests, self.attire = today, 0, [], {}
            for p in people:
                attire = p.get("attire") if isinstance(p, dict) else None
                if p.get("known") and p.get("slug") and isinstance(attire, dict):
                    self.attire[str(p["slug"])] = str(attire.get("color") or "")
            members = {str(m.get("person")) for m in audience.get("members") or [] if m.get("person")}
            for slug in sorted(members - self.members):
                self._person(slug, True, at)
            for slug in sorted(self.members - members):
                self._person(slug, False, at)
            self.members = members
            self._guests(max(0, min(32, int(audience.get("guests") or 0))), at)
            kind = audience.get("kind")
            if kind in SHUTTER and self.kind == "authorized":
                record.record("display.privacy_shutter", record.NUXIVA, "sentinel.display.privacy_shutter",
                              {"reason": SHUTTER[kind]}, "household", "display", at=at)
            self.kind = kind


collector = PresenceCollector()
