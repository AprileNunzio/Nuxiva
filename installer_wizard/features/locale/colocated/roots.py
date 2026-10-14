from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping

from features.locale.colocated.domain import Scope
from features.locale.colocated.errors import ScopeForbidden, ScopeRejected

LANGUAGE_DIR = "language"


@dataclass(frozen=True)
class ScopeRoots:
    roots: Mapping[str, tuple[Path, ...]]

    def candidates(self, scope: Scope, locale_code: str) -> Iterator[Path]:
        bases = self.roots.get(scope.root)
        if not bases:
            raise ScopeRejected("Unknown scope root")
        for base in bases:
            anchor = base.resolve()
            target = (anchor / scope.relative / LANGUAGE_DIR / f"{locale_code}.json").resolve()
            if not target.is_relative_to(anchor) or target.parent.name != LANGUAGE_DIR:
                raise ScopeForbidden("Scope escapes its root")
            yield target
