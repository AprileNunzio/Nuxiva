from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import IntEnum


class Strength(IntEnum):
    NONE = 0
    WEAK = 1
    SINGLE = 2
    STRONG = 3


@dataclass(frozen=True)
class Principal:
    slug: str = ""
    role: str = "anonymous"
    strength: Strength = Strength.NONE
    factors: tuple[str, ...] = field(default_factory=tuple)
    override: str = ""
    source: str = ""
    subrole: str = ""
    zones: tuple[str, ...] = field(default_factory=tuple)
    schedule: str = ""

    @property
    def known(self) -> bool:
        return bool(self.slug)

    def describe(self) -> dict:
        return {"slug": self.slug, "role": self.role, "subrole": self.subrole,
                "strength": self.strength.name.lower(), "factors": list(self.factors),
                "override": self.override, "zones": list(self.zones), "schedule": self.schedule}


ANONYMOUS = Principal()
SYSTEM = Principal(slug="nuxiva", role="system", strength=Strength.STRONG, factors=("system",))

current: ContextVar[Principal] = ContextVar("nuxiva_principal", default=ANONYMOUS)


def acting() -> Principal:
    return current.get()


def act_as(principal: Principal):
    return current.set(principal)
