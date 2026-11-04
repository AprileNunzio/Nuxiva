from dataclasses import dataclass
from typing import Callable

Status = Callable[[str], dict]


@dataclass(frozen=True)
class Connector:
    ident: str
    name: str
    icon: str
    status: Status


_registry: dict[str, Connector] = {}


def register(ident: str, name: str, icon: str, status: Status) -> None:
    _registry[ident] = Connector(ident, name, icon, status)


def listing(slug: str) -> list[dict]:
    rows = []
    for connector in _registry.values():
        try:
            detail = connector.status(slug)
        except Exception as exc:
            detail = {"available": False, "linked": False, "error": type(exc).__name__}
        rows.append({"id": connector.ident, "name": connector.name, "icon": connector.icon, **detail})
    return rows


def known() -> list[str]:
    return list(_registry)
