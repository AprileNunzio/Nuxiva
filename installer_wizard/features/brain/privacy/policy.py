import re
import threading
from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Mapping

from cryptography.fernet import InvalidToken
from sealed import SealedFile

from features.brain.privacy.levels import PERSONAL, PUBLIC, SENSITIVE

LOCAL, HOME, REMOTE = "local", "home", "remote"
ORIGINS = (LOCAL, HOME, REMOTE)
REACH = {"local": (LOCAL,), "home": (LOCAL, HOME), "any": ORIGINS}
CHOICES = tuple(REACH)
RANK = {choice: index for index, choice in enumerate(CHOICES)}
PROFILES = {
    "max": {"personal": "local", "sensitive": "local"},
    "balanced": {"personal": "home", "sensitive": "local"},
    "open": {"personal": "any", "sensitive": "any"},
}
CUSTOM = "custom"
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_PEOPLE = 500


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class Policy:
    profile: str
    personal: str
    sensitive: str

    def reach(self, level: str) -> tuple[str, ...]:
        if level == SENSITIVE:
            return REACH[self.sensitive]
        if level == PERSONAL:
            return REACH[self.personal]
        return ORIGINS

    def allows(self, level: str, origin: str) -> bool:
        return origin in self.reach(level if level in (PUBLIC, PERSONAL, SENSITIVE) else SENSITIVE)

    def to_json(self) -> dict:
        return asdict(self)


def preset(profile: str) -> Policy:
    return Policy(profile, **PROFILES[profile])


def parse(raw: object) -> Policy:
    if not isinstance(raw, Mapping):
        raise PolicyError("privacy_invalid")
    profile = raw.get("profile")
    if profile in PROFILES:
        return preset(profile)
    if profile != CUSTOM:
        raise PolicyError("privacy_invalid")
    personal, sensitive = raw.get("personal"), raw.get("sensitive")
    if personal not in REACH or sensitive not in REACH:
        raise PolicyError("privacy_invalid")
    if RANK[sensitive] > RANK[personal]:
        raise PolicyError("privacy_sensitive_looser")
    return Policy(CUSTOM, personal, sensitive)


def strictest(policies: Iterable[Policy]) -> Policy | None:
    chosen = list(policies)
    if not chosen:
        return None
    if len(chosen) == 1:
        return chosen[0]
    personal = min((p.personal for p in chosen), key=RANK.__getitem__)
    sensitive = min((p.sensitive for p in chosen), key=RANK.__getitem__)
    return Policy(CUSTOM, personal, sensitive)


def _load_entry(raw: object) -> Policy | None:
    try:
        return parse(raw)
    except PolicyError:
        return None


class PolicyStore:
    def __init__(self, sealed: SealedFile, local_engine: Callable[[], bool]) -> None:
        self._sealed = sealed
        self._local_engine = local_engine
        self._lock = threading.Lock()
        self._data: dict | None = None

    def _state(self) -> dict:
        if self._data is None:
            try:
                raw = self._sealed.load()
            except (OSError, ValueError, InvalidToken):
                raw = {}
            raw = raw if isinstance(raw, dict) else {}
            people = raw.get("people") if isinstance(raw.get("people"), dict) else {}
            self._data = {
                "default": _load_entry(raw.get("default")),
                "people": {slug: p for slug, entry in list(people.items())[:MAX_PEOPLE]
                           if isinstance(slug, str) and SLUG.match(slug) and (p := _load_entry(entry))},
            }
        return self._data

    def _persist(self, data: dict) -> None:
        self._sealed.save({"default": data["default"].to_json() if data["default"] else None,
                           "people": {slug: p.to_json() for slug, p in data["people"].items()}})

    def automatic(self) -> Policy:
        return preset("balanced" if self._local_engine() else "open")

    def default(self) -> Policy:
        with self._lock:
            chosen = self._state()["default"]
        return chosen or self.automatic()

    def default_is_automatic(self) -> bool:
        with self._lock:
            return self._state()["default"] is None

    def own(self, slug: str) -> Policy | None:
        with self._lock:
            return self._state()["people"].get(slug)

    def for_person(self, slug: str) -> Policy:
        return self.own(slug) or self.default()

    def for_people(self, slugs: Iterable[str]) -> Policy:
        return strictest(self.for_person(s) for s in dict.fromkeys(slugs)) or self.default()

    def set_default(self, raw: object) -> Policy:
        automatic = isinstance(raw, Mapping) and raw.get("profile") == "auto"
        chosen = None if automatic else parse(raw)
        with self._lock:
            data = self._state()
            data["default"] = chosen
            self._persist(data)
        return self.default()

    def set_person(self, slug: str, raw: object) -> Policy | None:
        if not SLUG.match(slug):
            raise PolicyError("privacy_unknown_person")
        inherit = isinstance(raw, Mapping) and raw.get("profile") == "inherit"
        chosen = None if inherit else parse(raw)
        with self._lock:
            data = self._state()
            if chosen is None:
                data["people"].pop(slug, None)
            elif slug in data["people"] or len(data["people"]) < MAX_PEOPLE:
                data["people"][slug] = chosen
            else:
                raise PolicyError("privacy_too_many")
            self._persist(data)
        return chosen
