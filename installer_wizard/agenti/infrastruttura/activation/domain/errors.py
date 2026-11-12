from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


class DomainError(Exception):
    def __init__(self, code: str, **params: object) -> None:
        super().__init__(code)
        self.code = code
        self.params: Mapping[str, object] = MappingProxyType({k: str(v)[:200] for k, v in params.items()})

    def to_dict(self) -> dict:
        return {"code": self.code, "params": dict(self.params)}


class SequenceError(DomainError):
    pass


class JourneyError(DomainError):
    pass
