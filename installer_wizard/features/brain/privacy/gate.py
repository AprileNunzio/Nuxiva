import time
from pathlib import Path
from typing import Callable, Iterable

from config import ETC_DIR
from sealed import SealedFile

from features.brain.privacy import origin as origins
from features.brain.privacy.audit import BLOCKED, PrivacyAudit
from features.brain.privacy.detector import classify_all
from features.brain.privacy.levels import PERSONAL, PUBLIC, component_level, strictest
from features.brain.privacy.policy import LOCAL, Policy, PolicyStore

PEOPLE_TTL = 60.0


class PrivacyBlocked(RuntimeError):
    def __init__(self, level: str) -> None:
        super().__init__(f"privacy_blocked:{level}")
        self.level = level


def _local_engine() -> bool:
    from features.brain.residency import primary
    return primary() is not None and origins.engine() == LOCAL


def _present() -> list[str]:
    from state import store
    return [str(p["slug"]) for p in store.presence.get("people", []) if p.get("known") and p.get("slug")]


class PeopleIndex:
    def __init__(self, ttl: float = PEOPLE_TTL) -> None:
        self._ttl = ttl
        self._at = -ttl
        self._owner: str | None = None
        self._names: tuple[str, ...] = ()

    def _refresh(self) -> None:
        if time.monotonic() - self._at < self._ttl:
            return
        from features.people import people
        try:
            profiles = people.all_profiles(light=True)
        except OSError:
            return
        owner = next((p for p in profiles if p.get("role") == "owner"), profiles[0] if len(profiles) == 1 else None)
        self._owner = str(owner["slug"]) if owner else None
        names = {str(p.get(k) or "").strip().lower() for p in profiles for k in ("first_name", "last_name", "nickname")}
        self._names = tuple(sorted(n for n in names if len(n) >= 3))
        self._at = time.monotonic()

    def owner(self) -> str | None:
        self._refresh()
        return self._owner

    def names(self) -> tuple[str, ...]:
        self._refresh()
        return self._names


class PrivacyGate:
    def __init__(self, store: PolicyStore, audit: PrivacyAudit, origin_of: Callable[[str], str] = origins.of,
                 present: Callable[[], list[str]] = _present, index: PeopleIndex | None = None) -> None:
        self.policies = store
        self.audit = audit
        self._origin_of = origin_of
        self._present = present
        self._index = index or PeopleIndex()

    def level(self, texts: Iterable[object], *, component: str = "", declared: str = "", personal: bool = False) -> str:
        return strictest(component_level(component), declared, PERSONAL if personal else PUBLIC,
                         classify_all(texts, self._index.names()))

    def policy(self, person: str = "") -> Policy:
        slugs = [person] if person else self._present()
        if not slugs:
            owner = self._index.owner()
            slugs = [owner] if owner else []
        return self.policies.for_people(slugs) if slugs else self.policies.default()

    def screen(self, models: list[str], level: str, person: str = "") -> list[str]:
        if not models:
            return models
        rule = self.policy(person)
        kept = [m for m in models if rule.allows(level, self._origin_of(m))]
        if not kept:
            self.audit.record(level, BLOCKED)
            raise PrivacyBlocked(level)
        return kept

    def served(self, ref: str, level: str) -> None:
        self.audit.record(level, self._origin_of(ref))


def build(directory: Path = ETC_DIR) -> PrivacyGate:
    store = PolicyStore(SealedFile(directory / "brain_privacy.vault", directory / "brain_privacy.key"), _local_engine)
    audit = PrivacyAudit(SealedFile(directory / "brain_privacy_audit.vault", directory / "brain_privacy_audit.key"))
    return PrivacyGate(store, audit)


privacy_gate = build()
