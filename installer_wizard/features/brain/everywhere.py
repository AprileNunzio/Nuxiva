import re
from dataclasses import replace
from typing import Mapping

from features.brain.assignments import MAX_ORDER, Assignment
from features.brain.roles import ROLES

_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$")


class EverywhereError(ValueError):
    pass


def clean_model(raw: object) -> str:
    model = str(raw or "").strip()
    if not _MODEL.match(model):
        raise EverywhereError("invalid model")
    return model


def _lead(model: str, rest: list[str] | tuple[str, ...], keep: bool) -> tuple[str, ...]:
    if not keep:
        return (model,)
    return tuple(dict.fromkeys([model, *rest]))[:MAX_ORDER]


def role_updates(model: str, chains: Mapping[str, list[str]], keep: bool) -> dict[str, str]:
    updates: dict[str, str] = {}
    for role in ROLES:
        updates[role.env_key] = ",".join(_lead(model, chains.get(role.id, []), keep))
        updates[role.profile_key] = "custom"
        updates[role.scope_key] = ""
        updates[role.strategy_key] = ""
    return updates


def assignment_updates(model: str, current: Mapping[str, Assignment], keep: bool) -> dict[str, Assignment]:
    return {cid: replace(a, order=_lead(model, a.order, keep), mode=a.mode if keep else "only")
            for cid, a in current.items() if a.order}
