from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from features.activation.domain.errors import SequenceError

MANIFEST_VERSION = 1
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
FILE_RE = re.compile(r"^[a-z0-9_]{1,48}\.(png|webp|js|py)$")
HARDWARE_FACTS = frozenset({"monitor", "camera", "bluetooth", "nvidia", "kvm", "microphone"})


class SequenceKind(str, Enum):
    MANDATORY = "mandatory"
    AUTO = "auto"
    OPTIONAL = "optional"
    CONFIGURE = "configure"


def _ident(value: object, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise SequenceError("sequence.invalid_identifier", field=field, value=value)
    return value


def _file(value: object, field: str) -> str:
    if value in ("", None):
        return ""
    if not isinstance(value, str) or not FILE_RE.fullmatch(value):
        raise SequenceError("sequence.invalid_file", field=field, value=value)
    return value


def _env(raw: object, owner: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, Mapping):
        raise SequenceError("sequence.invalid_env", owner=owner)
    pairs = []
    for key, value in raw.items():
        if not isinstance(key, str) or not ENV_RE.fullmatch(key) or not isinstance(value, str) or len(value) > 64:
            raise SequenceError("sequence.invalid_env", owner=owner, key=key)
        pairs.append((key, value))
    return tuple(sorted(pairs))


@dataclass(frozen=True)
class Condition:
    kind: str
    subject: str
    values: tuple[str, ...] = ()

    @classmethod
    def parse(cls, raw: object) -> Condition:
        kind, _, rest = str(raw).partition(":")
        if kind == "hardware":
            if rest not in HARDWARE_FACTS:
                raise SequenceError("sequence.unknown_hardware_fact", value=rest)
            return cls("hardware", rest)
        if kind == "choice":
            subject, _, values = rest.partition("=")
            options = tuple(_ident(v, "condition.value") for v in values.split("|") if v)
            if not options:
                raise SequenceError("sequence.empty_condition", value=raw)
            return cls("choice", _ident(subject, "condition.subject"), options)
        raise SequenceError("sequence.unknown_condition", value=raw)

    def holds(self, hardware: frozenset[str], choices: Mapping[str, str]) -> bool:
        if self.kind == "hardware":
            return self.subject in hardware
        return choices.get(self.subject, "") in self.values


@dataclass(frozen=True)
class Choice:
    id: str
    installs: bool
    icon: str = ""
    recommended: bool = False
    env: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_manifest(cls, raw: Mapping, owner: str) -> Choice:
        ident = _ident(raw.get("id"), "choice.id")
        return cls(id=ident, installs=raw.get("installs") is True, icon=_file(raw.get("icon"), "choice.icon"),
                   recommended=raw.get("recommended") is True, env=_env(raw.get("env", {}), f"{owner}.{ident}"))


@dataclass(frozen=True)
class Sequence:
    id: str
    kind: SequenceKind
    order: int
    steps: tuple[str, ...] = ()
    icon: str = ""
    critical: bool = False
    skippable: bool = False
    view: str = ""
    handler: str = ""
    when: tuple[Condition, ...] = ()
    choices: tuple[Choice, ...] = ()
    env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _ident(self.id, "id")
        if not 0 <= self.order <= 100_000:
            raise SequenceError("sequence.invalid_order", sequence=self.id)
        if len(set(self.steps)) != len(self.steps):
            raise SequenceError("sequence.duplicate_steps", sequence=self.id)
        for step in self.steps:
            _ident(step, "step")
        if self.critical and self.kind is not SequenceKind.MANDATORY:
            raise SequenceError("sequence.critical_not_mandatory", sequence=self.id)
        if self.skippable and self.kind is not SequenceKind.CONFIGURE:
            raise SequenceError("sequence.skippable_not_configure", sequence=self.id)
        if self.choices and self.kind is not SequenceKind.OPTIONAL:
            raise SequenceError("sequence.choices_not_optional", sequence=self.id)
        if self.kind is SequenceKind.CONFIGURE:
            self._check_configure()
        else:
            self._check_installer()
        if self.kind is SequenceKind.OPTIONAL:
            self._check_choices()

    def _check_configure(self) -> None:
        if not self.view or not self.handler:
            raise SequenceError("sequence.configure_without_view", sequence=self.id)
        if self.steps:
            raise SequenceError("sequence.configure_with_steps", sequence=self.id)

    def _check_installer(self) -> None:
        if not self.steps:
            raise SequenceError("sequence.missing_steps", sequence=self.id)
        if self.view or self.handler:
            raise SequenceError("sequence.installer_with_view", sequence=self.id)

    def _check_choices(self) -> None:
        ids = [c.id for c in self.choices]
        if len(ids) < 2 or len(set(ids)) != len(ids):
            raise SequenceError("sequence.invalid_choices", sequence=self.id)
        if all(c.installs for c in self.choices) or not any(c.installs for c in self.choices):
            raise SequenceError("sequence.choices_need_yes_and_no", sequence=self.id)
        if sum(c.recommended for c in self.choices) > 1:
            raise SequenceError("sequence.multiple_recommended", sequence=self.id)

    @property
    def awaits_user(self) -> bool:
        return self.kind in (SequenceKind.OPTIONAL, SequenceKind.CONFIGURE)

    def choice(self, choice_id: str) -> Choice:
        for choice in self.choices:
            if choice.id == choice_id:
                return choice
        raise SequenceError("sequence.unknown_choice", sequence=self.id, choice=choice_id)

    def applies(self, hardware: frozenset[str], choices: Mapping[str, str]) -> bool:
        return all(condition.holds(hardware, choices) for condition in self.when)

    @classmethod
    def from_manifest(cls, raw: object) -> Sequence:
        if not isinstance(raw, Mapping):
            raise SequenceError("sequence.manifest_not_object")
        if raw.get("manifest_version") != MANIFEST_VERSION:
            raise SequenceError("sequence.unsupported_manifest", value=raw.get("manifest_version"))
        ident = _ident(raw.get("id"), "id")
        kind_raw, order, steps = raw.get("kind"), raw.get("order"), raw.get("steps", [])
        if kind_raw not in {k.value for k in SequenceKind}:
            raise SequenceError("sequence.unknown_kind", sequence=ident, value=kind_raw)
        if not isinstance(order, int) or isinstance(order, bool):
            raise SequenceError("sequence.invalid_order", sequence=ident)
        choices = raw.get("choices", [])
        if not isinstance(steps, list) or not isinstance(raw.get("when", []), list) or not isinstance(choices, list):
            raise SequenceError("sequence.invalid_list", sequence=ident)
        if not all(isinstance(c, Mapping) for c in choices):
            raise SequenceError("sequence.invalid_choices", sequence=ident)
        return cls(id=ident, kind=SequenceKind(kind_raw), order=order, steps=tuple(steps),
                   icon=_file(raw.get("icon"), "icon"), critical=raw.get("critical") is True,
                   skippable=raw.get("skippable") is True, view=_file(raw.get("view"), "view"),
                   handler=_file(raw.get("handler"), "handler"),
                   when=tuple(Condition.parse(c) for c in raw.get("when", [])),
                   choices=tuple(Choice.from_manifest(c, ident) for c in choices),
                   env=_env(raw.get("env", {}), ident))
